import os
import json
import logging
import asyncio
import subprocess
import httpx
from typing import Dict, Any
from core.config import ENABLE_AUTO_BACKUP, GITHUB_TOKEN

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
        self.repo_name = "logichive-vault-backup"
        self._initialized_remote = False
        
    async def _initialize_remote_repo_api(self) -> bool:
        """
        Uses GitHub API to ensure a private backup repo exists and is linked.
        """
        if not GITHUB_TOKEN:
            logger.error("AutoBackup: GITHUB_TOKEN is missing in .env. Remote sync is disabled.")
            return False

        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with httpx.AsyncClient() as client:
                # 1. Get current user
                logger.debug("AutoBackup: Fetching GitHub user info...")
                try:
                    user_res = await client.get("https://api.github.com/user", headers=headers, timeout=10.0)
                except Exception as e:
                    logger.error(f"AutoBackup: Network error calling GitHub API: {e}")
                    return False

                if user_res.status_code != 200:
                    logger.error(f"AutoBackup: GitHub Auth Failed ({user_res.status_code}): {user_res.text}")
                    return False
                
                username = user_res.json()["login"]
                logger.info(f"AutoBackup: Authenticated as GitHub user: {username}")
                
                # 2. Check if repo exists
                repo_url = f"https://api.github.com/repos/{username}/{self.repo_name}"
                check_res = await client.get(repo_url, headers=headers)
                
                if check_res.status_code == 404:
                    # 3. Create private repo
                    logger.info(f"AutoBackup: Creating private repository '{self.repo_name}'...")
                    create_res = await client.post(
                        "https://api.github.com/user/repos",
                        headers=headers,
                        json={
                            "name": self.repo_name,
                            "private": True,
                            "description": "LogicHive Vault Auto-Backup"
                        }
                    )
                    if create_res.status_code not in (201, 200):
                        logger.error(f"AutoBackup: Repository creation failed: {create_res.text}")
                        return False
                    logger.info(f"AutoBackup: Successfully created '{self.repo_name}' on GitHub.")
                
                # 4. Initialize local git if needed
                if not os.path.exists(os.path.join(self.export_dir, ".git")):
                    logger.info(f"AutoBackup: Initializing local Git repository in {self.export_dir}...")
                    os.makedirs(self.export_dir, exist_ok=True)
                    res_init = subprocess.run(["git", "init"], cwd=self.export_dir, capture_output=True, text=True)
                    if res_init.returncode != 0:
                        logger.error(f"AutoBackup: 'git init' failed: {res_init.stderr}")
                        return False
                    subprocess.run(["git", "branch", "-M", "main"], cwd=self.export_dir, capture_output=True)
                
                # 5. Add remote (using token for auth)
                # Note: We mask the token in logs
                remote_auth_url = f"https://{GITHUB_TOKEN}@github.com/{username}/{self.repo_name}.git"
                subprocess.run(["git", "remote", "remove", "origin"], cwd=self.export_dir, capture_output=True)
                res_remote = subprocess.run(["git", "remote", "add", "origin", remote_auth_url], cwd=self.export_dir, capture_output=True, text=True)
                
                if res_remote.returncode == 0:
                    logger.info(f"AutoBackup: Remote 'origin' configured successfully.")
                    # 6. Pull existing content (like README.md)
                    logger.debug("AutoBackup: Pulling existing content from remote...")
                    subprocess.run(["git", "pull", "origin", "main", "--rebase"], cwd=self.export_dir, capture_output=True)
                    self._initialized_remote = True
                    return True
                else:
                    logger.error(f"AutoBackup: 'git remote add' failed: {res_remote.stderr}")
                    
        except Exception as e:
            logger.error(f"AutoBackup: Unexpected error during initialization: {e}")
        return False
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

    async def bulk_sync_to_git(self) -> None:
        """
        Performs a single commit and push for all exported assets.
        Useful for initial migration or force-backup.
        """
        try:
            if not self._initialized_remote:
                await self._initialize_remote_repo_api()
            
            if not os.path.exists(os.path.join(self.export_dir, ".git")):
                return

            # Add all
            await (await asyncio.create_subprocess_exec("git", "add", ".", cwd=self.export_dir)).wait()
            
            # Commit
            commit_proc = await asyncio.create_subprocess_exec(
                "git", "commit", "-m", "backup: bulk export of all assets", 
                cwd=self.export_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await commit_proc.communicate()
            
            # Push
            push_proc = await asyncio.create_subprocess_exec(
                "git", "push", "-u", "origin", "main",
                cwd=self.export_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            p_out, p_err = await push_proc.communicate()
            
            if push_proc.returncode == 0:
                logger.info("AutoBackup: Successfully completed bulk backup to GitHub.")
            else:
                logger.error(f"AutoBackup: Bulk push failed (code {push_proc.returncode}): {p_err.decode().strip()}")
                
        except Exception as e:
            logger.error(f"AutoBackup: Bulk sync failed: {e}")

    async def sync_to_git(self, name: str) -> None:
        """
        Runs git commands in the exports/ directory to sync with the private backup repo.
        """
        try:
            # Try to initialize if not already done
            if not self._initialized_remote:
                await self._initialize_remote_repo_api()

            # 1. Check if exports exists and is a git repo
            if not os.path.exists(os.path.join(self.export_dir, ".git")):
                return

            # 2. Check if git is installed
            try:
                check_git = await asyncio.create_subprocess_exec(
                    "git", "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await check_git.communicate()
                if check_git.returncode != 0:
                    return
            except FileNotFoundError:
                return

            # 3. Execute git commands WITHIN exports/
            # Step A: Add all changes in exports/
            await (await asyncio.create_subprocess_exec("git", "add", ".", cwd=self.export_dir)).wait()
            
            # Step B: Commit
            commit_proc = await asyncio.create_subprocess_exec(
                "git", "commit", "-m", f"backup: {name}", 
                cwd=self.export_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await commit_proc.communicate()
            
            # Step C: Push to private remote
            push_proc = await asyncio.create_subprocess_exec(
                "git", "push", "-u", "origin", "main",
                cwd=self.export_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await push_proc.communicate()
            
            if push_proc.returncode == 0:
                logger.info(f"AutoBackup: Successfully backed up '{name}' to private repository.")
            
        except Exception as e:
            logger.error(f"AutoBackup: Private Git sync failed for '{name}': {e}")

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
