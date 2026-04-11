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