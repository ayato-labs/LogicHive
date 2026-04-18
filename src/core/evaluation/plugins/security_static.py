import ast
import logging
import re
from typing import Any

from ..base import BaseEvaluator, EvaluationResult

logger = logging.getLogger(__name__)

class SecurityStaticEvaluator(BaseEvaluator):
    """
    Deterministic security auditor inspired by Rigour's SecurityVisitor.
    Performs AST analysis to detect structural vulnerabilities without LLM guessing.
    """

    @property
    def name(self) -> str:
        return "security_static"

    async def evaluate(self, code: str, language: str, **kwargs) -> EvaluationResult:
        if language.lower() != "python":
            return EvaluationResult(score=100.0, reason="Security static analysis skipped for non-python language.")

        issues = []
        try:
            tree = ast.parse(code)
            visitor = SecurityVisitor(code)
            visitor.visit(tree)
            visitor.check_sql_injection()
            issues = visitor.issues
        except Exception as e:
            return EvaluationResult(score=0.0, reason=f"Syntax error or AST parsing failed: {e}")

        if not issues:
            return EvaluationResult(score=100.0, reason="No structural security vulnerabilities detected.")

        # Scoring: Deduct 40 points per CRITICAL issue, 10 per WEAK issue
        score = 100.0
        details = []
        for issue in issues:
            severity = issue.get("severity", "high")
            deduction = 40.0 if severity == "high" else 10.0
            score -= deduction
            details.append(f"L{issue['lineno']}: {issue['message']}")

        score = max(0.0, score)
        return EvaluationResult(
            score=score,
            reason=f"Security flaws detected: {'; '.join(details)}",
            details={"vulnerabilities": issues}
        )

class SecurityVisitor(ast.NodeVisitor):
    def __init__(self, content: str):
        self.issues = []
        self.content = content
        self.lines = content.split('\n')

    def visit_Assign(self, node: ast.Assign):
        """Detect hardcoded secrets."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id.upper()
                # Targets: API_KEY, PASSWORD, TOKEN, SECRET, etc.
                pattern = r"(API_KEY|PASSWORD|TOKEN|AUTH_TOKEN|PRIVATE_KEY|AWS_SECRET|SECRET_KEY)"
                if re.search(pattern, name):
                    if isinstance(node.value, (ast.Constant, ast.Str)):
                        val = node.value.value if isinstance(node.value, ast.Constant) else node.value.s
                        if isinstance(val, str) and len(val) > 4: # Ignore very short strings
                            self.issues.append({
                                "issue": "hardcoded_secret",
                                "lineno": node.lineno,
                                "severity": "high",
                                "message": f"Potential hardcoded secret in variable '{target.id}'"
                            })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Detect dangerous function calls."""
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        # 1. Code Injection
        if func_name in ("eval", "exec"):
            self.issues.append({
                "issue": "code_injection",
                "lineno": node.lineno,
                "severity": "high",
                "message": f"Dangerous usage of '{func_name}' detected."
            })

        # 2. Insecure Deserialization
        if func_name in ("loads", "load"):
            # Check for pickle or yaml.unsafe_load
            prefix = ""
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                prefix = node.func.value.id
            
            if prefix == "pickle":
                self.issues.append({
                    "issue": "insecure_deserialization",
                    "lineno": node.lineno,
                    "severity": "high",
                    "message": "Pickle usage is insecure. Use JSON for untrusted data."
                })

        # 3. Command Injection (subprocess with shell=True)
        if func_name in ("run", "call", "Popen", "check_call", "check_output"):
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant):
                    if keyword.value.value is True:
                        self.issues.append({
                            "issue": "command_injection",
                            "lineno": node.lineno,
                            "severity": "high",
                            "message": f"Subprocess '{func_name}' called with shell=True."
                        })

        self.generic_visit(node)

    def check_sql_injection(self):
        """Regex-based catch for obvious SQL injection patterns."""
        patterns = [
            (r"\.execute\(f[\"']", "F-string SQL query"),
            (r"\.execute\(.*\%", "String formatting (%) in SQL query"),
            (r"\.execute\(.*\+", "String concatenation in SQL query")
        ]
        for pattern, msg in patterns:
            for i, line in enumerate(self.lines, 1):
                if re.search(pattern, line):
                    self.issues.append({
                        "issue": "sql_injection",
                        "lineno": i,
                        "severity": "high",
                        "message": f"Potential SQL injection detected: {msg}"
                    })
