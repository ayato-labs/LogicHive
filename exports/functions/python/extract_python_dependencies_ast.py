def extract_python_dependencies(code: str) -> list[str]:
    import ast

    dependencies = set()
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    base = alias.name.split(".")[0]
                    dependencies.add(base)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    base = node.module.split(".")[0]
                    dependencies.add(base)
    except SyntaxError:
        return []

    std_lib = {
        "os",
        "sys",
        "json",
        "math",
        "datetime",
        "typing",
        "asyncio",
        "logging",
        "ast",
        "pathlib",
        "uuid",
        "abc",
    }
    return sorted(list(dependencies - std_lib))
