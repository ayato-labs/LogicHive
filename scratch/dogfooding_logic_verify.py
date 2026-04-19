import ast
import re

# Logic Atom 1: Assertion Counter
def count_assertions_python(test_code: str) -> int:
    if not test_code.strip():
        return 0
    
    def is_constant_expr(node: ast.AST) -> bool:
        if hasattr(ast, "Constant") and isinstance(node, ast.Constant):
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
            if isinstance(node, ast.Assert):
                if is_constant_expr(node.test):
                    continue
                count += 1
            elif isinstance(node, ast.Call):
                is_assert_func = False
                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id.startswith("assert")
                    or isinstance(node.func, ast.Attribute)
                    and node.func.attr.startswith("assert")
                ):
                    is_assert_func = True

                if is_assert_func:
                    if all(is_constant_expr(arg) for arg in node.args):
                        continue
                    count += 1
        return count
    except SyntaxError:
        return 0

# Logic Atom 2: Hollow Logic Detector
def find_hollow_methods(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
        hollow = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = [
                    n
                    for n in node.body
                    if not (
                        isinstance(n, ast.Expr)
                        and isinstance(n.value, ast.Constant)
                        and isinstance(n.value.value, str)
                    )
                ]
                if not body:
                    hollow.append(node.name)
                    continue
                if len(body) == 1:
                    stmt = body[0]
                    if isinstance(stmt, ast.Pass) or (
                        isinstance(stmt, ast.Expr)
                        and isinstance(stmt.value, ast.Constant)
                        and stmt.value.value is Ellipsis
                    ):
                        hollow.append(node.name)
                    elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Name):
                        arg_names = [a.arg for a in node.args.args]
                        if stmt.value.id in arg_names:
                            hollow.append(node.name)
        return hollow
    except SyntaxError:
        return []

# Logic Atom 3: Code Hasher
import hashlib
def calculate_code_hash(code: str) -> str:
    normalized_code = code.strip().replace("\r\n", "\n")
    return hashlib.sha256(normalized_code.encode("utf-8")).hexdigest()

# Tests for verification
if __name__ == "__main__":
    # Test Assertion Counter
    test_suite = "assert 1 == 1\nassert foo == bar\npytest.assume(x > 0)"
    print(f"Assertions: {count_assertions_python(test_suite)}") # Should be 2 (1==1 is constant)
    
    # Test Hollow Detector
    code_with_hollow = "def ok():\n  return 1\ndef empty():\n  pass\ndef dots():\n  ...\ndef identity(x):\n  return x"
    print(f"Hollows: {find_hollow_methods(code_with_hollow)}") # ['empty', 'dots', 'identity']
    
    print(f"Hash: {calculate_code_hash('print(1)')}")
