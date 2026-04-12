import asyncio
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from core.execution.pool import PoolManager, PreWarmedEnv

@pytest.fixture
async def pool_manager():
    import time
    # Setup a dedicated test pool dir with a unique subfolder to avoid collisions
    import uuid
    test_id = str(uuid.uuid4())[:8]
    test_pool_dir = Path(f"storage/data/test/pools_unit_{test_id}")
    
    def force_rmtree(path):
        for _ in range(5):
            try:
                if path.exists():
                    shutil.rmtree(path)
                return
            except PermissionError:
                time.sleep(0.5)
        # Final attempt
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    with patch("core.execution.pool.POOL_BASE_DIR", str(test_pool_dir)), \
         patch("core.execution.pool.POOL_MAX_SIZE", 0): # Don't auto-prepare in unit tests
        manager = PoolManager()
        manager.has_gpu = False 
        await manager.initialize()
        yield manager
        await manager.shutdown()
        # Ensure task is really gone
        if manager._worker_task:
            try:
                await manager._worker_task
            except asyncio.CancelledError:
                pass

    force_rmtree(test_pool_dir)

@pytest.mark.asyncio
async def test_pool_manager_initialization(pool_manager):
    assert pool_manager.base_dir.exists()
    assert "torch-cpu" in pool_manager.pools
    assert "torch-gpu" in pool_manager.pools

@pytest.mark.asyncio
async def test_pool_manager_acquire_timeout(pool_manager):
    # Try to acquire something from an empty pool with short timeout
    env = await pool_manager.acquire("torch-cpu", timeout=0.1)
    assert env is None

@pytest.mark.asyncio
async def test_pool_manager_prepare_env(pool_manager):
    # Manually trigger preparation for a small spec or mock it
    # Preparation takes time and depends on network/uv. 
    # For unit tests, we'll mock the subprocess call.
    from unittest.mock import AsyncMock
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Mock uv venv and uv pip install
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.returncode = 0
        mock_exec.return_value = mock_process
        
        await pool_manager._prepare_env("torch-cpu")
        
        # Verify it was added to the queue
        assert pool_manager.pools["torch-cpu"].qsize() == 1
        env = await pool_manager.acquire("torch-cpu")
        assert env is not None
        assert "torch-cpu" in env.path.name

@pytest.mark.asyncio
async def test_pool_manager_gpu_fallback(pool_manager):
    # If no GPU detected, torch-gpu request should fallback to torch-cpu
    pool_manager.has_gpu = False
    
    # Mock CPU pool having an item
    cpu_env = PreWarmedEnv("torch-cpu", Path("test_path"), Path("python.exe"))
    await pool_manager.pools["torch-cpu"].put(cpu_env)
    
    env = await pool_manager.acquire("torch-gpu")
    assert env == cpu_env
    assert env.spec_name == "torch-cpu"
