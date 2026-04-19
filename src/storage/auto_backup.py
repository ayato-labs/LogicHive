import asyncio
import json
import logging
import os
import subprocess
from typing import Any

import httpx

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
            if ENABLE_AUTO_BACKUP:
                logger.debug("AutoBackup: GITHUB_TOKEN is not set. Skipping remote sync.")
            return False

        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }

            async with httpx.AsyncClient() as client:
                # 1. Get current user
                logger.debug("AutoBackup: Fetching GitHub user info...")
                try:
                    user_res = await client.get(
                        "https://api.github.com/user", headers=headers, timeout=10.0
                    )
                except Exception as e:
                    logger.error(f"AutoBackup: Network error calling GitHub API: {e}")
                    return False

                if user_res.status_code != 200:
                    logger.error(
                        f"AutoBackup: GitHub Auth Failed ({user_res.status_code}): {user_res.text}"
                    )
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
                            "description": "LogicHive Vault Auto-Backup",
                        },
                    )
                    if create_res.status_code not in (201, 200):
                        logger.error(f"AutoBackup: Repository creation failed: {create_res.text}")
                        return False
                    logger.info(f"AutoBackup: Successfully created '{self.repo_name}' on GitHub.")

                # 4. Initialize local git if needed
                if not os.path.exists(os.path.join(self.export_dir, ".git")):
                    logger.info(
                        f"AutoBackup: Initializing local Git repository in {self.export_dir}..."
                    )
                    os.makedirs(self.export_dir, exist_ok=True)
                    res_init = subprocess.run(
                        ["git", "init"],
                        cwd=self.export_dir,
                        capture_output=True,
                        text=True,
                    )
                    if res_init.returncode != 0:
                        logger.error(f"AutoBackup: 'git init' failed: {res_init.stderr}")
                        return False
                    subprocess.run(
                        ["git", "branch", "-M", "main"],
                        cwd=self.export_dir,
                        capture_output=True,
                    )

                # 5. Add remote (using token for auth)
                # Note: We mask the token in logs
                remote_auth_url = (
                    f"https://{GITHUB_TOKEN}@github.com/{username}/{self.repo_name}.git"
                )
                subprocess.run(
                    ["git", "remote", "remove", "origin"],
                    cwd=self.export_dir,
                    capture_output=True,
                )
                res_remote = subprocess.run(
                    ["git", "remote", "add", "origin", remote_auth_url],
                    cwd=self.export_dir,
                    capture_output=True,
                    text=True,
                )

                if res_remote.returncode == 0:
                    logger.info("AutoBackup: Remote 'origin' configured successfully.")
                    # 6. Pull existing content (like README.md)
                    logger.debug("AutoBackup: Pulling existing content from remote...")
                    subprocess.run(
                        ["git", "pull", "origin", "main", "--rebase"],
                        cwd=self.export_dir,
                        capture_output=True,
                    )
                    self._initialized_remote = True
                    return True
                else:
                    logger.error(f"AutoBackup: 'git remote add' failed: {res_remote.stderr}")

        except Exception as e:
            logger.error(f"AutoBackup: Unexpected error during initialization: {e}")
        return False

    def _get_extension(self, language: str) -> str:
        mapping = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "markdown": "md",
            "json": "json",
        }
        return mapping.get(language.lower(), "txt")

    async def export_asset(self, data: dict[str, Any]) -> None:
        """
        Exports the asset (code and metadata) to the exports/ directory.
        """
        name = data.get("name", "unknown")
        project = data.get("project", "default")
        language = data.get("language", "text")
        code = data.get("code", "")

        # 1. Create directory structure: exports/projects/{project}/...
        project_dir = os.path.join(self.export_dir, "projects", project)
        func_dir = os.path.join(project_dir, "functions", language.lower())
        meta_dir = os.path.join(project_dir, "metadata")
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

        logger.debug(f"AutoBackup: Exported '{name}' in project '{project}' to {self.export_dir}")

    async def bulk_export(self, assets: list[dict[str, Any]]) -> None:
        """
        Exports multiple assets to files.
        """
        for asset in assets:
            await self.export_asset(asset)
        logger.info(f"AutoBackup: Bulk export completed for {len(assets)} assets.")

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
            await (
                await asyncio.create_subprocess_exec("git", "add", ".", cwd=self.export_dir)
            ).wait()

            # Commit
            commit_proc = await asyncio.create_subprocess_exec(
                "git",
                "commit",
                "-m",
                "backup: bulk export of all assets",
                cwd=self.export_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await commit_proc.communicate()

            # Push
            push_proc = await asyncio.create_subprocess_exec(
                "git",
                "push",
                "-u",
                "origin",
                "main",
                cwd=self.export_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            p_out, p_err = await push_proc.communicate()

            if push_proc.returncode == 0:
                logger.info("AutoBackup: Successfully completed bulk backup to GitHub.")
            else:
                logger.error(
                    f"AutoBackup: Bulk push failed (code {push_proc.returncode}): {p_err.decode().strip()}"
                )

        except Exception as e:
            logger.error(f"AutoBackup: Bulk sync failed: {e}")

    async def get_all_backup_assets(self) -> list[dict[str, Any]]:
        """
        Pulls from Git and returns a list of all asset dictionaries found in the backup.
        """
        assets = []
        try:
            # 1. Sync from remote
            if not self._initialized_remote:
                await self._initialize_remote_repo_api()

            if not os.path.exists(os.path.join(self.export_dir, ".git")):
                logger.error("AutoBackup: Git repository not initialized.")
                return []

            logger.info("AutoBackup: Pulling latest backup from GitHub...")
            pull_res = subprocess.run(
                ["git", "pull", "origin", "main", "--rebase"],
                cwd=self.export_dir,
                capture_output=True,
                text=True,
            )
            if pull_res.returncode != 0:
                logger.warning(f"AutoBackup: Pull failed: {pull_res.stderr}")

            # 2. Iterate metadata JSONs in all project subdirectories
            projects_root = os.path.join(self.export_dir, "projects")
            if not os.path.exists(projects_root):
                return []

            for project in os.listdir(projects_root):
                project_path = os.path.join(projects_root, project)
                if not os.path.isdir(project_path):
                    continue

                meta_dir = os.path.join(project_path, "metadata")
                if not os.path.exists(meta_dir):
                    continue

                for filename in os.listdir(meta_dir):
                    if not filename.endswith(".json"):
                        continue

                    try:
                        meta_path = os.path.join(meta_dir, filename)
                        with open(meta_path, encoding="utf-8") as f:
                            meta_data = json.load(f)

                        name = meta_data.get("name")
                        lang = meta_data.get("language", "python")
                        # Ensure project is set in metadata if missing
                        if "project" not in meta_data:
                            meta_data["project"] = project

                        ext = self._get_extension(lang)

                        # Read source code if available
                        code_path = os.path.join(
                            project_path, "functions", lang.lower(), f"{name}.{ext}"
                        )
                        if os.path.exists(code_path):
                            with open(code_path, encoding="utf-8") as f:
                                meta_data["code"] = f.read()

                        assets.append(meta_data)
                    except Exception as e:
                        logger.error(
                            f"AutoBackup: Failed to read '{filename}' in project '{project}': {e}"
                        )

        except Exception as e:
            logger.error(f"AutoBackup: Error listing backup assets: {e}")

        return assets

    async def restore_from_git(self) -> dict[str, Any]:
        """
        High-level restoration: Gets assets from Git and upserts them using the orchestrator or local DB.
        Note: The actual DB sync is now triggered elsewhere to avoid circularity.
        """
        # This keeps the method signature for compatibility but it's now a stub or uses local import carefully
        results = {"success": 0, "failed": 0, "errors": []}
        assets = await self.get_all_backup_assets()

        # We'll use a local import here, but only if absolutely necessary
        try:
            from storage.sqlite_api import sqlite_storage

            for asset in assets:
                try:
                    await sqlite_storage.upsert_function(asset)
                    results["success"] += 1
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"{asset.get('name')}: {e}")
        except ImportError:
            results["errors"].append("Could not import sqlite_storage for restoration.")

        return results

    async def sync_to_git(self, name: str, project: str = "default") -> None:
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
                    "git",
                    "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await check_git.communicate()
                if check_git.returncode != 0:
                    return
            except FileNotFoundError:
                return

            # 3. Execute git commands WITHIN exports/
            # Step A: Add all changes in exports/
            await (
                await asyncio.create_subprocess_exec("git", "add", ".", cwd=self.export_dir)
            ).wait()

            # Step B: Commit
            commit_proc = await asyncio.create_subprocess_exec(
                "git",
                "commit",
                "-m",
                f"backup: [{project}] {name}",
                cwd=self.export_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await commit_proc.communicate()

            # Step C: Push to private remote
            push_proc = await asyncio.create_subprocess_exec(
                "git",
                "push",
                "-u",
                "origin",
                "main",
                cwd=self.export_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await push_proc.communicate()

            if push_proc.returncode == 0:
                logger.info(
                    f"AutoBackup: Successfully backed up '{name}' ({project}) to private repository."
                )

        except Exception as e:
            logger.error(f"AutoBackup: Private Git sync failed for '{name}' ({project}): {e}")

    async def archive_asset(self, name: str, project: str = "default") -> None:
        """
        Moves the asset files to an archives/ directory and syncs with Git.
        """
        try:
            # 1. Sync from remote
            if not self._initialized_remote:
                await self._initialize_remote_repo_api()

            # 2. Identify files within the project directory
            found_files = []
            project_dir = os.path.join(self.export_dir, "projects", project)

            # Check metadata
            meta_path = os.path.join(project_dir, "metadata", f"{name}.json")
            lang = "unknown"
            if os.path.exists(meta_path):
                found_files.append(meta_path)
                with open(meta_path, encoding="utf-8") as f:
                    try:
                        meta = json.load(f)
                        lang = meta.get("language", "unknown")
                    except (OSError, json.JSONDecodeError) as e:
                        logger.warning(
                            f"AutoBackup: Failed to read metadata for '{name}' at {meta_path}: {e}"
                        )

            # Check functions
            ext = self._get_extension(lang)
            code_path = os.path.join(project_dir, "functions", lang.lower(), f"{name}.{ext}")
            if os.path.exists(code_path):
                found_files.append(code_path)

            if not found_files:
                logger.info(
                    f"AutoBackup: No files found to archive for '{name}' in project '{project}'."
                )
                return

            # 3. Move to archives directory (keeping project context)
            import datetime

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_base = os.path.join(self.export_dir, "archives", timestamp, project, name)
            os.makedirs(archive_base, exist_ok=True)

            for fpath in found_files:
                target = os.path.join(archive_base, os.path.basename(fpath))
                os.rename(fpath, target)

            # 4. Git sync
            await (
                await asyncio.create_subprocess_exec("git", "add", ".", cwd=self.export_dir)
            ).wait()
            commit_proc = await asyncio.create_subprocess_exec(
                "git",
                "commit",
                "-m",
                f"archive: [{project}] {name}",
                cwd=self.export_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await commit_proc.communicate()

            await (
                await asyncio.create_subprocess_exec(
                    "git", "push", "origin", "main", cwd=self.export_dir
                )
            ).wait()
            logger.info(f"AutoBackup: Successfully archived '{name}' ({project}) to Git.")

        except Exception as e:
            logger.error(f"AutoBackup: Archiving failed for '{name}' ({project}): {e}")

    async def process_backup(self, data: dict[str, Any]) -> None:
        """
        Full backup flow: Export then Sync.
        """
        if not ENABLE_AUTO_BACKUP:
            return

        try:
            await self.export_asset(data)
            await self.sync_to_git(
                data.get("name", "asset"), project=data.get("project", "default")
            )
        except Exception as e:
            logger.error(f"AutoBackup: Background backup process failed: {e}")


# Singleton instance
backup_manager = AutoBackupManager()
