import ast

from ..base import BaseEvaluator, EvaluationResult


class DeterministicEvaluator(BaseEvaluator):
    """
    Evaluates Python code using deterministic structural analysis (AST).
    Checks for presence of assertions and absence of "hollow" logic.
    """

    @property
    def name(self) -> str:
        return "deterministic"

    async def evaluate(self, code: str, language: str, **kwargs) -> EvaluationResult:
        lang = language.lower()
        test_code = kwargs.get("test_code", "")
        reasons = []
        score = 100.0
        
        # 1. Multi-Language Assertion Detection
        if lang == "python":
            assertion_count = self._count_assertions_python(test_code)
            is_valid_test = self._verify_test_calls_code_python(code, test_code)
        else:
            # Basic support for JS/C++/Java assertions via Regex
            assertion_count = self._count_assertions_regex(test_code, lang)
            is_valid_test = True # Structural check only for non-python for now
            reasons.append(f"Notice: Deterministic audit for '{lang}' uses structural pattern matching (Level 2).")

        # 2. Hollow Logic Detection (Python only for now)
        hollow_methods = self._find_hollow_methods(code) if lang == "python" else []
        heavy_imports = self._find_heavy_imports(code) if lang == "python" else []

        # -- Scoring Logic --

        # A. Zero Assertion Rule (Hard Reject)
        if assertion_count == 0:
            score = 0.0
            reasons.append("CRITICAL: No assertions found in test code. Testing is performative only.")
        elif assertion_count < 3:
            score -= (3 - assertion_count) * 20
            reasons.append(f"Low test density: only {assertion_count} assertions found.")
        else:
            reasons.append(f"Satisfactory test density ({assertion_count} assertions).")

        # B. Call Graph Verification (Anti-Theater)
        if lang == "python" and assertion_count > 0 and not is_valid_test:
            score *= 0.5 # Severe penalty for not calling the code
            reasons.append("THEATER WARNING: Test code has assertions but NEVER CALLS any function from the target logic.")

        # C. Hollow Logic Penalty
        if hollow_methods:
            penalty = min(len(hollow_methods) * 30, 80)
            score -= penalty
            reasons.append(f"Hollow logic detected in methods: {', '.join(hollow_methods)}")

        # D. Performance Warning
        if heavy_imports:
            score -= min(len(heavy_imports) * 5, 20)
            reasons.append(f"Performance Warning: Heavy imports detected ({', '.join(heavy_imports)}).")

        score = max(0.0, score)

        return EvaluationResult(
            score=score,
            reason=" | ".join(reasons),
            details={
                "assertion_count": assertion_count,
                "hollow_methods": hollow_methods,
                "heavy_imports": heavy_imports,
                "is_valid_test": is_valid_test
            }
        )

    def _count_assertions_python(self, test_code: str) -> int:
        if not test_code.strip():
            return 0
        try:
            tree = ast.parse(test_code)
            count = 0
            for node in ast.walk(tree):
                # 1. Direct assert statements
                if isinstance(node, ast.Assert):
                    # ANTI-THEATER: Check for constant assertions (assert True, assert 1 == 1)
                    if self._is_constant_expr(node.test):
                        continue # Skip theatrical assertions
                    count += 1
                # 2. Call to assert functions (pytest.assume, unittest methods, etc)
                elif isinstance(node, ast.Call):
                    is_assert_func = False
                    if isinstance(node.func, ast.Name) and node.func.id.startswith("assert"):
                        is_assert_func = True
                    elif isinstance(node.func, ast.Attribute) and node.func.attr.startswith("assert"):
                        is_assert_func = True
                    
                    if is_assert_func:
                        # Skip if all arguments are constants
                        if all(self._is_constant_expr(arg) for arg in node.args):
                            continue
                        count += 1
            return count
        except SyntaxError:
            return 0

    def _is_constant_expr(self, node: ast.AST) -> bool:
        """Determines if an expression is evaluation-time constant (trivial)."""
        # Handle Python 3.8+ Constant node
        if hasattr(ast, "Constant") and isinstance(node, ast.Constant):
            return True
        # Handle older Python and specific constant-like structures
        if isinstance(node, (ast.Num, ast.Str, ast.Bytes, ast.NameConstant)):
            return True
        # Handle common trivial comparisons: 1 == 1, True is True
        if isinstance(node, ast.Compare):
            if self._is_constant_expr(node.left) and all(self._is_constant_expr(comp) for comp in node.comparators):
                return True
        return False

    def _verify_test_calls_code_python(self, code: str, test_code: str) -> bool:
        """Checks if test_code calls any function or class defined in code."""
        try:
            code_tree = ast.parse(code)
            test_tree = ast.parse(test_code)
            
            # Find all public definitions in code
            defined_names = set()
            for node in ast.walk(code_tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if not node.name.startswith("_"): # Focus on public API
                        defined_names.add(node.name)
            
            if not defined_names:
                return True # Nothing defined to call
                
            # Check if any defined name is called or referenced in test_code
            for node in ast.walk(test_tree):
                if isinstance(node, ast.Name) and node.id in defined_names:
                    return True
                if isinstance(node, ast.Attribute) and node.attr in defined_names:
                    return True
            return False
        except SyntaxError:
            return True # Fallback on error

    def _count_assertions_regex(self, test_code: str, lang: str) -> int:
        """Fallback assertion counter using Regex for non-Python languages."""
        import re
        
        patterns = {
            "javascript": r"(expect|assert)\(.*\)",
            "typescript": r"(expect|assert)\(.*\)",
            "cpp": r"(assert|EXPECT_|ASSERT_)\(.*\)",
            "java": r"assert(True|False|Equals|NotNull|Same)\(.*\)"
        }
        
        pattern = patterns.get(lang.lower(), r"assert.*\(.*\)")
        matches = re.findall(pattern, test_code)
        
        # Basic constant filtering via heuristic
        valid_matches = 0
        for m in matches:
            # Heuristic: If it looks like assert(true) or assert(1 == 1)
            inner = m.lower()
            if "true" in inner or "false" in inner or "1==1" in inner or "1 == 1" in inner:
                if len(inner) < 20: # Simple constant assertions are usually short
                    continue
            valid_matches += 1
            
        return valid_matches

    def _find_hollow_methods(self, code: str) -> list[str]:
        try:
            tree = ast.parse(code)
            hollow = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    body = [n for n in node.body if not (
                        isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
                    )]
                    if not body:
                        hollow.append(node.name)
                        continue
                    if len(body) == 1:
                        stmt = body[0]
                        if isinstance(stmt, ast.Pass) or (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis):
                            hollow.append(node.name)
                        elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Name):
                            arg_names = [a.arg for a in node.args.args]
                            if stmt.value.id in arg_names:
                                hollow.append(node.name)
            return hollow
        except SyntaxError:
            return []

    def _find_heavy_imports(self, code: str) -> list[str]:
        HEAVY_LIBS = {"torch", "tensorflow", "sklearn", "pandas", "matplotlib", "seaborn", "scipy"}
        heavy_found = []
        try:
            tree = ast.parse(code)
            for node in tree.body:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        base_mod = alias.name.split('.')[0]
                        if base_mod in HEAVY_LIBS:
                            heavy_found.append(base_mod)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        base_mod = node.module.split('.')[0]
                        if base_mod in HEAVY_LIBS:
                            heavy_found.append(base_mod)
            return list(set(heavy_found))
        except SyntaxError:
            return []
