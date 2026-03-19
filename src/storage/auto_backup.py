import os
import json
import logging
import asyncio
import subprocess
from typing import Dict, Any
from core.config import ENABLE_AUTO_BACKUP

logger = logging.getLogger(__name__)

class AutoBackupManager:
    """
    Handles background export and Git synchronization of LogicHive assets.
    """
    
    def __init__(self, base_dir: str = None):
        # Default to project root (assumed to be one level up from src)
        if base_dir is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.base_dir = base_dir
        self.export_dir = os.path.join(self.base_dir, "exports")
        
    def _get_extension(self, language: str) -> str:
        mapping = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "markdown": "md",
            "json": "json"
        }
        return mapping.get(language.lower(), "txt")

    async def export_asset(self, data: Dict[str, Any]) -> None:
        """
        Exports the asset (code and metadata) to the exports/ directory.
        """
        name = data.get("name", "unknown")
        language = data.get("language", "text")
        code = data.get("code", "")
        
        # 1. Create directory structure
        func_dir = os.path.join(self.export_dir, "functions", language.lower())
        meta_dir = os.path.join(self.export_dir, "metadata")
        os.makedirs(func_dir, exist_ok=True)
        os.makedirs(meta_dir, exist_ok=True)
        
        # 2. Write Code File
        ext = self._get_extension(language)
        code_path = os.path.join(func_dir, f"{name}.{ext}")
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        # 3. Write Metadata JSON (excluding embedding for readability)
        meta_path = os.path.join(meta_dir, f"{name}.json")
        meta_data = {k: v for k, v in data.items() if k != "embedding"}
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=4, ensure_ascii=False)
            
        logger.debug(f"AutoBackup: Exported '{name}' to {self.export_dir}")

    async def sync_to_git(self, name: str) -> None:
        """
        Runs git commands to commit and push the exports/ folder.
        Safely handles cases where git is missing or repo is not configured.
        """
        try:
            # 1. Check if this is a git repo
            if not os.path.exists(os.path.join(self.base_dir, ".git")):
                logger.debug("AutoBackup: No .git directory found. Sync skipped (Local backup only).")
                return

            # 2. Check if git is installed
            try:
                # Use subprocess to check if git command works
                check_git = await asyncio.create_subprocess_exec(
                    "git", "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await check_git.communicate()
                if check_git.returncode != 0:
                    logger.warning("AutoBackup: 'git' command returned non-zero. Remote sync disabled.")
                    return
            except FileNotFoundError:
                logger.warning("AutoBackup: 'git' command not found in PATH. Remote sync disabled (Local backup only).")
                return

            # 3. Execute git commands
            # We use specifically 'exports/' to avoid committing WIP files in other dirs
            # Note: 'git push' might fail if no remote is set, we handle that individually.
            
            # Step A: Add
            await (await asyncio.create_subprocess_exec("git", "add", "exports/", cwd=self.base_dir)).wait()
            
            # Step B: Commit
            commit_proc = await asyncio.create_subprocess_exec(
                "git", "commit", "-m", f"backup: auto-sync {name}", 
                cwd=self.base_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await commit_proc.communicate()
            
            # Step C: Push (Check if remote exists first)
            remote_proc = await asyncio.create_subprocess_exec(
                "git", "remote",
                cwd=self.base_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            r_out, _ = await remote_proc.communicate()
            if b"origin" not in r_out:
                logger.info(f"AutoBackup: No 'origin' remote found. Local commit only for '{name}'.")
                return

            push_proc = await asyncio.create_subprocess_exec(
                "git", "push", "origin", "main",
                cwd=self.base_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            p_out, p_err = await push_proc.communicate()
            
            if push_proc.returncode == 0:
                logger.info(f"AutoBackup: Successfully synced '{name}' to GitHub.")
            else:
                logger.warning(f"AutoBackup: Git push failed: {p_err.decode().strip()}")
                
        except Exception as e:
            logger.error(f"AutoBackup: Git sync failed for '{name}': {e}")

    async def process_backup(self, data: Dict[str, Any]) -> None:
        """
        Full backup flow: Export then Sync.
        """
        if not ENABLE_AUTO_BACKUP:
            return
            
        try:
            await self.export_asset(data)
            await self.sync_to_git(data.get("name", "asset"))
        except Exception as e:
            logger.error(f"AutoBackup: Background backup process failed: {e}")

# Singleton instance
backup_manager = AutoBackupManager()
