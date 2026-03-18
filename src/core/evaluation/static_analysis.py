import logging
import ast
import re
from typing import List, Dict, Any
from .base import BaseEvaluator, EvaluationResult

logger = logging.getLogger(__name__)

class StructuralEvaluator(BaseEvaluator):
    """
    Evaluates basic structural integrity (e.g. unbalanced brackets).
    This is language-agnostic.
    """
    @property
    def name(self) -> str:
        return "structural"

    async def evaluate(self, code: str, language: str, **kwargs) -> EvaluationResult:
        unbalanced = []
        pairs = {'(': ')', '[': ']', '{': '}'}
        stack = []
        for char in code:
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack or pairs[stack.pop()] != char:
                    unbalanced.append(char)
                    break
        
        if stack or unbalanced:
            return EvaluationResult(score=0.0, reason="Structural error detected (unbalanced brackets).")
        
        return EvaluationResult(score=100.0, reason="Structural integrity passed.")

class PythonStaticEvaluator(BaseEvaluator):
    """
    Performs Python-specific static checks using AST.
    Checks for relative imports and complex project-specific dependencies.
    """
    @property
    def name(self) -> str:
        return "python_static"

    async def evaluate(self, code: str, language: str, **kwargs) -> EvaluationResult:
        if language.lower() != "python":
            return EvaluationResult(score=100.0, reason="Skipped (Not Python).")

        score = 100.0
        reasons = []

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if "." in alias.name:
                            score -= 5
                            reasons.append(f"Deep import detected: {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.level > 0:
                        score -= 10
                        reasons.append("Relative import detected.")
            
            # Additional heuristic: check for too many functions in one asset
            func_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
            if func_count > 1:
                score -= 10
                reasons.append(f"Contains {func_count} functions (Atomicity risk).")

        except SyntaxError as e:
            return EvaluationResult(score=0.0, reason=f"Python Syntax Error: {e}")
        
        reason_str = " | ".join(reasons) if reasons else "Static checks passed."
        return EvaluationResult(score=max(0.0, score), reason=reason_str)
