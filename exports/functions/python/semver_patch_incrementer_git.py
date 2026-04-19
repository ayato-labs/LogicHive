def get_next_version(git_tags: list[str], default_start: str = "v1.0.0") -> str:
    if not git_tags or git_tags == [""]:
        return default_start

    def version_key(v):
        try:
            return list(map(int, v[1:].split(".")))
        except:
            return [0, 0, 0]

    valid_tags = [t for t in git_tags if t.startswith("v") and "." in t]
    if not valid_tags:
        return default_start
    valid_tags.sort(key=version_key)
    latest = valid_tags[-1]
    parts = version_key(latest)
    parts[-1] += 1
    return f"v{'.'.join(map(str, parts))}"
