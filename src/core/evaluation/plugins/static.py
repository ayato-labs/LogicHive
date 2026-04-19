import ast
import asyncio
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from ..base import BaseEvaluator, EvaluationResult

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
        pairs = {"(": ")", "[": "]", "{": "}"}
        stack = []
        for char in code:
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack or pairs[stack.pop()] != char:
                    unbalanced.append(char)
                    break

        if stack or unbalanced:
            return EvaluationResult(
                score=0.0, reason="Structural error detected (unbalanced brackets)."
            )

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


class RuffEvaluator(BaseEvaluator):
    """
    Evaluates Python code using the Ruff linter.
    """

    @property
    def name(self) -> str:
        return "ruff"

    async def evaluate(self, code: str, language: str, **kwargs) -> EvaluationResult:
        if language.lower() != "python":
            return EvaluationResult(score=100.0, reason="Skipped (Not Python).")

        try:
            import shutil

            from core.config import PROJECT_ROOT

            # 1. Search for ruff in PATH
            ruff_cmd = shutil.which("ruff")

            # 2. Fallback to local .venv (common in this repository's setup)
            if not ruff_cmd:
                venv_ruff = Path(PROJECT_ROOT) / ".venv" / "Scripts" / "ruff.exe"
                if venv_ruff.exists():
                    ruff_cmd = str(venv_ruff)
                else:
                    # Final fallback to see if it's in the same directory as python
                    import sys

                    python_dir = Path(sys.executable).parent
                    alt_ruff = python_dir / ("ruff.exe" if os.name == "nt" else "ruff")
                    if alt_ruff.exists():
                        ruff_cmd = str(alt_ruff)
                    else:
                        ruff_cmd = "ruff"  # Last resort

            # Use subprocess to run ruff check on stdin
            process = await asyncio.create_subprocess_exec(
                ruff_cmd,
                "check",
                "--output-format",
                "json",
                "-",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate(input=code.encode())

            if process.returncode not in [0, 1]:  # Ruff returns 1 if it finds issues
                # Check if ruff is installed/callable
                error_msg = stderr.decode().strip() or stdout.decode().strip()
                logger.warning(f"Ruff execution failed or not found: {error_msg}")
                return EvaluationResult(score=100.0, reason="Ruff not available, skipped.")

            issues = json.loads(stdout.decode())
            if not issues:
                return EvaluationResult(score=100.0, reason="Ruff: No issues found. (Ideal state)")

            # Scoring logic: Deduct points for each issue
            score = 100.0
            issue_summaries = []

            # Group by code to avoid repetitiveness
            for issue in issues[:5]:  # Cap feedback to avoid token bloat
                code = issue.get("code", "UNK")
                msg = issue.get("message", "No message")
                line = issue.get("location", {}).get("row", "?")
                issue_summaries.append(f"[{code}] L{line}: {msg}")

            score -= len(issues) * 2.0
            score = max(0.0, score)

            summary_text = " | ".join(issue_summaries)
            if len(issues) > 5:
                summary_text += f" ...and {len(issues) - 5} more issues."

            return EvaluationResult(
                score=score,
                reason=f"Ruff: Found {len(issues)} issues. {summary_text}",
            )

        except Exception as e:
            logger.warning(f"RuffEvaluator Error: {e}")
            return EvaluationResult(score=100.0, reason=f"Ruff check skipped due to error: {e}")


class ESLintEvaluator(BaseEvaluator):
    """
    Evaluates JavaScript/TypeScript code using ESLint.
    """

    @property
    def name(self) -> str:
        return "eslint"

    async def evaluate(self, code: str, language: str, **kwargs) -> EvaluationResult:
        supported_langs = [
            "javascript",
            "typescript",
            "javascriptreact",
            "typescriptreact",
        ]
        if language.lower() not in supported_langs:
            return EvaluationResult(score=100.0, reason="Skipped (Not JS/TS).")

        # Determine extension
        ext = ".js"
        if "typescript" in language.lower():
            ext = ".ts"
        if "react" in language.lower():
            ext += "x"

        with tempfile.NamedTemporaryFile(
            suffix=ext, delete=False, mode="w", encoding="utf-8"
        ) as tmp:
            tmp_path = tmp.name
            tmp.write(code)

        try:
            # Run eslint --format json --no-eslintrc (or similar minimalist call)
            # Note: eslint usually needs a config. We assume a project config is present or skip.
            process = await asyncio.create_subprocess_exec(
                "npx",
                "eslint",
                "--format",
                "json",
                tmp_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode not in [0, 1]:
                return EvaluationResult(
                    score=100.0,
                    reason="ESLint not available or no config found, skipped.",
                )

            results = json.loads(stdout.decode())
            if not results or not results[0].get("messages"):
                return EvaluationResult(score=100.0, reason="ESLint: No issues found.")

            messages = results[0]["messages"]
            score = 100.0
            for msg in messages:
                # severity 2 is error, 1 is warning
                if msg.get("severity") == 2:
                    score -= 5.0
                else:
                    score -= 1.0

            score = max(0.0, score)
            return EvaluationResult(
                score=score,
                reason=f"ESLint: Found {len(messages)} issues. (Score: {score})",
            )

        except Exception as e:
            return EvaluationResult(score=100.0, reason=f"ESLint check failed: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
