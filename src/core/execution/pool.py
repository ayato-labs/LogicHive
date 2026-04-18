import asyncio
import logging
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from core.config import DEFAULT_POOL_SPECS, ENABLE_ENV_POOLING, POOL_BASE_DIR, POOL_MAX_SIZE

logger = logging.getLogger(__name__)

class PreWarmedEnv:
    """Represents a single ready-to-go virtual environment."""
    def __init__(self, spec_name: str, path: Path, python_executable: Path):
        self.spec_name = spec_name
        self.path = path
        self.python_executable = python_executable
        self.created_at = asyncio.get_event_loop().time()

class PoolManager:
    """
    Manages pools of pre-warmed virtual environments to eliminate 'Cold Start' latency.
    """
    _instance: Optional["PoolManager"] = None

    def __init__(self):
        self.base_dir = Path(POOL_BASE_DIR)
        self.pools: Dict[str, asyncio.Queue[PreWarmedEnv]] = {
            spec: asyncio.Queue() for spec in DEFAULT_POOL_SPECS
        }
        self.active_envs: Dict[str, PreWarmedEnv] = {}
        self.has_gpu = self._detect_gpu()
        self._worker_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "PoolManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _detect_gpu(self) -> bool:
        """Detects if an NVIDIA GPU is available and functional."""
        try:
            # Quick check using nvidia-smi
            result = subprocess.run(
                ["nvidia-smi"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False

    async def initialize(self):
        """Prepares the pool directory and starts the background worker."""
        if not ENABLE_ENV_POOLING:
            logger.info("PoolManager: Pooling is disabled in config.")
            return

        def _sync_cleanup():
            try:
                os.makedirs(self.base_dir, exist_ok=True)
                # Cleanup old pools on startup
                for item in self.base_dir.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
            except Exception as e:
                logger.error(f"PoolManager: Initial cleanup failed: {e}")

        # Run cleanup in a thread to keep MCP server responsive
        await asyncio.to_thread(_sync_cleanup)
        
        logger.info(f"PoolManager: Initialized at {self.base_dir} (GPU Detected: {self.has_gpu})")
        self._worker_task = asyncio.create_task(self._background_worker())

    async def shutdown(self):
        """Stops the worker and cleans up all environments."""
        if self._worker_task:
            self._worker_task.cancel()
        
        # Cleanup directories
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir, ignore_errors=True)
        logger.info("PoolManager: Shutdown and cleaned up.")

    async def acquire(self, spec_name: str, timeout: float = 5.0) -> Optional[PreWarmedEnv]:
        """Safely takes an environment from the pool."""
        if not ENABLE_ENV_POOLING:
            return None

        if spec_name not in self.pools:
            return None
        
        # Skip GPU pool if no GPU detected, fallback to CPU
        if spec_name == "torch-gpu" and not self.has_gpu:
            spec_name = "torch-cpu"

        try:
            env = await asyncio.wait_for(self.pools[spec_name].get(), timeout=timeout)
            logger.info(f"PoolManager: Acquired {spec_name} environment: {env.path.name}")
            return env
        except asyncio.TimeoutError:
            logger.warning(f"PoolManager: Timeout waiting for {spec_name} pool. Falling back to cold start.")
            return None

    async def release(self, env: PreWarmedEnv):
        """Discards a used environment."""
        # Environments are single-use to ensure isolation
        def cleanup():
            if env.path.exists():
                shutil.rmtree(env.path, ignore_errors=True)
        
        # Run cleanup in thread to avoid blocking loop
        await asyncio.to_thread(cleanup)
        logger.debug(f"PoolManager: Released and deleted {env.path.name}")

    async def _background_worker(self):
        """Keeps pools filled up to POOL_MAX_SIZE."""
        logger.info("PoolManager: Background worker STARTED.")
        while True:
            try:
                for spec_name, queue in self.pools.items():
                    if not ENABLE_ENV_POOLING:
                        continue
                        
                    current_size = queue.qsize()
                    if current_size < POOL_MAX_SIZE:
                        # Don't spend resources on GPU pool if no GPU
                        if spec_name == "torch-gpu" and not self.has_gpu:
                            continue
                        
                        logger.debug(f"PoolManager: Replenishing {spec_name}")
                        await self._prepare_env(spec_name)
                
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"PoolManager: Worker error: {e}")
                await asyncio.sleep(10)

    async def _prepare_env(self, spec_name: str):
        """Creates a new venv and installs dependencies using uv."""
        env_id = str(uuid.uuid4())[:8]
        env_path = self.base_dir / f"{spec_name}_{env_id}"
        
        # Path to uv.exe (absolute path for reliability on Windows)
        uv_path = r"C:\Users\saiha\.local\bin\uv.exe"
        if not os.path.exists(uv_path):
            uv_path = "uv" # fallback
            
        # Determine python executable path (Windows specific)
        python_exe = env_path / "Scripts" / "python.exe" if os.name == "nt" else env_path / "bin" / "python"

        logger.info(f"PoolManager: Preparing {spec_name} ({env_id}) using {uv_path}...")
        debug_log(f"PoolManager: Starting preparation of {spec_name} ({env_id})")
        
        def run_cmd(cmd):
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=True
            )

        try:
            # 1. Create venv
            vcmd = f'"{uv_path}" venv "{env_path}"'
            res = await asyncio.to_thread(run_cmd, vcmd)
            
            if res.returncode != 0:
                logger.error(f"PoolManager: uv venv failed: {res.stderr}")
                raise Exception(f"uv venv failed for {spec_name}")

            # 2. Install packages
            packages = DEFAULT_POOL_SPECS.get(spec_name, [])
            if packages:
                pkg_str = " ".join(packages)
                python_exe_str = str(python_exe)
                icmd = f'"{uv_path}" pip install --python "{python_exe_str}" {pkg_str}'
                
                res = await asyncio.to_thread(run_cmd, icmd)
                
                if res.returncode != 0:
                    logger.error(f"PoolManager: uv pip install failed: {res.stderr}")
                    raise Exception(f"uv pip install failed for {spec_name}")

            # 3. Add to pool
            new_env = PreWarmedEnv(spec_name, env_path, python_exe)
            await self.pools[spec_name].put(new_env)
            logger.info(f"PoolManager: {spec_name} ({env_id}) is READY.")
            
        except Exception as e:
            logger.error(f"PoolManager: Failed to prepare {spec_name}: {e}")
            if env_path.exists():
                shutil.rmtree(env_path, ignore_errors=True)
