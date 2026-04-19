import ast
import hashlib
import re

# Logic Atom 1: count_assertions_python
# Original Source: src/core/evaluation/plugins/deterministic.py
def count_assertions_python(test_code: str) -> int:
    \"\"\"
    Counts actual assertions in Python test code using AST.
    Filters out 'theatrical' assertions like 'assert True'.
    \"\"\"
    if not test_code.strip():
        return 0

    def is_constant_expr(node: ast.AST) -> bool:
        if hasattr(ast, \"Constant\") and isinstance(node, ast.Constant):
            return True
        if isinstance(node, (ast.Num, ast.Str, ast.Bytes, ast.NameConstant)):
            return True
        if isinstance(node, ast.Compare):
            if is_constant_expr(node.left) and all(
                is_constant_expr(comp) for comp in node.comparators
            ):
                return True
        return False

    try:
        tree = ast.parse(test_code)
        count = 0
        for node in ast.walk(tree):
            # Direct assert statements
            if isinstance(node, ast.Assert):
                if is_constant_expr(node.test):
                    continue
                count += 1
            # Call to assert functions (pytest, unittest)
            elif isinstance(node, ast.Call):
                is_assert_func = False
                if (
                    isinstance(node.func, ast.Name) and node.func.id.startswith(\"assert\")
                    or isinstance(node.func, ast.Attribute) and node.func.attr.startswith(\"assert\")
                ):
                    is_assert_func = True

                if is_assert_func:
                    if all(is_constant_expr(arg) for arg in node.args):
                        continue
                    count += 1
        return count
    except SyntaxError:
        return 0

# Logic Atom 2: find_hollow_methods
# Original Source: src/core/evaluation/plugins/deterministic.py
def find_hollow_methods(code: str) -> list:
    \"\"\"
    Identifies methods that are 'hollow' (pass, ..., or simple identity return).
    \"\"\"
    try:
        tree = ast.parse(code)
        hollow = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Ignore docstrings
                body = [
                    n for n in node.body
                    if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str))
                ]
                if not body:
                    hollow.append(node.name)
                    continue
                if len(body) == 1:
                    stmt = body[0]
                    if isinstance(stmt, ast.Pass) or (
                        isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis
                    ):
                        hollow.append(node.name)
                    elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Name):
                        arg_names = [a.arg for a in node.args.args]
                        if stmt.value.id in arg_names:
                            hollow.append(node.name)
        return hollow
    except SyntaxError:
        return []

# Logic Atom 3: extract_dependencies
# Original Source: src/core/evaluation/plugins/dependency_vouch.py
def extract_dependencies(code: str) -> set:
    \"\"\"
    Extracts high-level module names from Python code using AST.
    \"\"\"
    try:
        tree = ast.parse(code)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    imports.add(node.module.split('.')[0])
        return imports
    except SyntaxError:
        return set()

# Logic Atom 4: calculate_code_hash
# Original Source: src/core/hash_utils.py
def calculate_code_hash(code: str) -> str:
    \"\"\"
    Calculates a SHA-256 hash for source code with basic normalization.
    \"\"\"
    normalized_code = code.strip().replace(\"\\r\\n\", \"\\n\")
    return hashlib.sha256(normalized_code.encode(\"utf-8\")).hexdigest()
