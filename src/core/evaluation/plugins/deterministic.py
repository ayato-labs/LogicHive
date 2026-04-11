import ast
from typing import List
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
        if language.lower() != "python":
            return EvaluationResult(score=100.0, reason="Skipped (Non-Python deterministic audit not yet implemented).")

        test_code = kwargs.get("test_code", "")
        
        # Audit Test Rigor
        assertion_count = self._count_assertions(test_code)
        
        # Audit Code Substance
        hollow_methods = self._find_hollow_methods(code)
        
        reasons = []
        score = 100.0
        
        # 1. Zero Assertion Rule (Hard Reject)
        if assertion_count == 0:
            score = 0.0
            reasons.append("CRITICAL: No assertions found in test code. Testing is performative only.")
        elif assertion_count < 3:
            score -= (3 - assertion_count) * 20
            reasons.append(f"Low test density: only {assertion_count} assertions found.")
        else:
            reasons.append(f"Satisfactory test density ({assertion_count} assertions).")

        # 2. Hollow Logic Detection
        if hollow_methods:
            penalty = min(len(hollow_methods) * 30, 80)
            score -= penalty
            reasons.append(f"Hollow logic detected in methods: {', '.join(hollow_methods)}")
        
        # Cap score
        score = max(0.0, score)
        
        return EvaluationResult(
            score=score,
            reason=" | ".join(reasons),
            details={
                "assertion_count": assertion_count,
                "hollow_methods": hollow_methods
            }
        )

    def _count_assertions(self, test_code: str) -> int:
        if not test_code.strip():
            return 0
        try:
            tree = ast.parse(test_code)
            count = 0
            for node in ast.walk(tree):
                # Direct assert statements
                if isinstance(node, ast.Assert):
                    count += 1
                # Call to assert functions (pytest.assume, unittest methods, etc)
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id.startswith("assert"):
                        count += 1
                    elif isinstance(node.func, ast.Attribute) and node.func.attr.startswith("assert"):
                        count += 1
            return count
        except SyntaxError:
            return 0

    def _find_hollow_methods(self, code: str) -> List[str]:
        try:
            tree = ast.parse(code)
            hollow = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Filter out docstrings/comments to see real body
                    body = [n for n in node.body if not (
                        isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
                    )]
                    
                    if not body or len(body) == 0:
                        hollow.append(node.name)
                        continue
                        
                    # Check for 'pass' or '...'
                    if len(body) == 1:
                        stmt = body[0]
                        if isinstance(stmt, ast.Pass):
                            hollow.append(node.name)
                        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis:
                            hollow.append(node.name)
                        # Check for identity return: def f(x): return x
                        elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Name):
                            # If returning an argument directly with no logic
                            arg_names = [a.arg for a in node.args.args]
                            if stmt.value.id in arg_names:
                                hollow.append(node.name)
            return hollow
        except SyntaxError:
            return []
