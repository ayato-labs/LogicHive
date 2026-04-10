import subprocess
import sys


def run_command(command, check=True):
    print(f"[EXEC] {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"[ERROR] {result.stderr}")
        sys.exit(result.returncode)
    return result


def get_next_version():
    """Fetches the latest v* tag and increments the patch version."""
    try:
        result = subprocess.run(
            ["git", "tag", "-l", "v*"], capture_output=True, text=True
        )
        tags = result.stdout.strip().split("\n")
        if not tags or tags == [""]:
            return "v2.2.1"  # Default starting point for this branch

        # Sort and get latest
        tags.sort(key=lambda s: list(map(int, s[1:].split("."))))
        latest = tags[-1]

        parts = list(map(int, latest[1:].split(".")))
        parts[-1] += 1
        return f"v{'.'.join(map(str, parts))}"
    except Exception as e:
        print(f"[WARNING] Could not determine next version: {e}")
        return None


def main():
    print("=== LogicHive Edge CD (GitHub) ===")
    print("[NOTE] Linting and Testing are now handled by GitHub Actions CI.")

    # 1. Versioning
    next_ver = get_next_version()
    print(f"\n[INFO] Target Version: {next_ver}")

    # 2. Check for changes
    status = run_command(["git", "status", "--porcelain"])
    if not status.stdout.strip():
        # Check if we should still release even if no code changes (e.g. forced update)
        print("\n[INFO] No changes to deploy to GitHub.")
        return

    # 3. Add and commit
    print("\n[INFO] Committing changes...")
    run_command(["git", "add", "."])

    try:
        commit_msg = input(
            f"Enter commit message (Enter for 'release: {next_ver}'): "
        ).strip()
    except EOFError:
        commit_msg = ""

    if not commit_msg:
        commit_msg = f"release: {next_ver}"

    run_command(["git", "commit", "-m", commit_msg])

    # 4. Tag and Push
    if next_ver:
        print(f"\n[INFO] Tagging with {next_ver}...")
        run_command(["git", "tag", next_ver])

    print("\n[INFO] Pushing to GitHub (origin main and tags)...")
    run_command(["git", "push", "origin", "main"])
    if next_ver:
        run_command(["git", "push", "origin", next_ver])

    print("\n[SUCCESS] Edge changes pushed!")
    print("[INFO] GitHub Actions CI/CD will now run tests and build the EXE.")


if __name__ == "__main__":
    main()
