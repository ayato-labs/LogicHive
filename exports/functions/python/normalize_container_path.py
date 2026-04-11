def normalize_container_path(path: str) -> str:
    """
    Converts Windows-style paths to POSIX-style paths for compatibility with Docker containers.
    """
    return path.replace("\\\\", "/")
