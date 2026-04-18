import ast
import logging
from typing import Any

from ..base import BaseEvaluator, EvaluationResult

logger = logging.getLogger(__name__)

class MetricsGateEvaluator(BaseEvaluator):
    """
    Code complexity and quality gate inspired by Rigour's MetricsVisitor.
    Evaluates maintainability based on cyclomatic complexity and parameter counts.
    """

    @property
    def name(self) -> str:
        return "metrics_gate"

    async def evaluate(self, code: str, language: str, **kwargs) -> EvaluationResult:
        if language.lower() != "python":
            return EvaluationResult(score=100.0, reason="Metrics analysis skipped for non-python language.")

        try:
            tree = ast.parse(code)
            visitor = MetricsVisitor()
            visitor.visit(tree)
            metrics = visitor.metrics
        except Exception as e:
            return EvaluationResult(score=0.0, reason=f"Syntax error prevented metrics analysis: {e}")

        if not metrics:
            return EvaluationResult(score=100.0, reason="No measurable code structures (functions/classes) found.")

        total_deduction = 0.0
        warnings = []
        
        for m in metrics:
            if m["type"] == "function":
                # 1. Cyclomatic Complexity gate (Threshold: 10)
                if m["complexity"] > 10:
                    severity = (m["complexity"] - 10) * 15 # Even stronger deduction
                    total_deduction += severity
                    warnings.append(f"Function '{m['name']}' (L{m['lineno']}) is too complex (CC={m['complexity']}).")
                
                # 2. Parameter count gate (Threshold: 6)
                if m["parameters"] > 6:
                    total_deduction += 30 # Even stronger deduction
                    warnings.append(f"Function '{m['name']}' (L{m['lineno']}) has too many parameters ({m['parameters']}).")

        score = max(0.0, 100.0 - total_deduction)
        
        if score >= 80.0: 
            reason = "Code metrics within acceptable range."
        else:
            reason = f"Poor maintainability metrics: {'; '.join(warnings)}"

        return EvaluationResult(
            score=score,
            reason=reason,
            details={"metrics": metrics}
        )

class MetricsVisitor(ast.NodeVisitor):
    def __init__(self):
        self.metrics = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.analyze_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.analyze_function(node)
        self.generic_visit(node)

    def analyze_function(self, node):
        # Cyclomatic Complexity calculation
        complexity = 1
        for n in ast.walk(node):
            if isinstance(n, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.Try, ast.ExceptHandler, ast.With, ast.AsyncWith)):
                complexity += 1
            elif isinstance(n, ast.BoolOp):
                complexity += len(n.values) - 1
            elif isinstance(n, ast.IfExp):
                complexity += 1

        # Parameter count
        params = len(node.args.args) + len(node.args.kwonlyargs)
        if node.args.vararg: params += 1
        if node.args.kwarg: params += 1

        self.metrics.append({
            "type": "function",
            "name": node.name,
            "complexity": complexity,
            "parameters": params,
            "lineno": node.lineno
        })
