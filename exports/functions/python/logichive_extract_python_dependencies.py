def extract_python_dependencies(code: str) -> List[str]:
    """
    Deterministically extracts top-level imports from Python code using AST.
    Filters out obvious project-internal relative imports.
    """
    dependencies = set()
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Get base package name (e.g., 'os' from 'os.path')
                    base = alias.name.split(".")[0]
                    dependencies.add(base)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    base = node.module.split(".")[0]
                    dependencies.add(base)
    except SyntaxError as e:
        logger.error(f"Orchestrator: Syntax error during dependency extraction: {e}")
        # For personal use, we assume code is generally correct, but syntax error is a hard failure.
        raise ValidationError(f"Python Syntax Error in provided code: {e}")
    except Exception as e:
        logger.error(f"Orchestrator: AST dependency extraction failed unexpectedly: {e}")
        # In personal mode, we might want to proceed but log the failure clearly.
        # However, per improvement plan, we should handle this more strictly.
        raise LogicHiveError(f"Critical failure during dependency extraction: {e}")

    # Filter out common standard libraries to keep the 'recipe' focused on external deps
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
