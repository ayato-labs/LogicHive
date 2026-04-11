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