import logging
import asyncio
import importlib
import pkgutil
from typing import List, Dict, Any, Optional
from .base import BaseEvaluator, EvaluationResult

logger = logging.getLogger(__name__)


class EvaluationManager:
    """
    Coordinates multiple evaluators to determine the final quality score.
    Now supports dynamic plugin loading from the .plugins package.
    """

    def __init__(self):
        self.evaluators: List[BaseEvaluator] = []
        self._load_plugins()

    def _load_plugins(self):
        """
        Dynamically discovers and instantiates all BaseEvaluator subclasses
        defined in the .plugins sub-package.
        """
        try:
            # Import the plugins package
            package_name = f"{__package__}.plugins"
            package = importlib.import_module(package_name)

            for loader, name, is_pkg in pkgutil.walk_packages(
                package.__path__, package.__name__ + "."
            ):
                module = importlib.import_module(name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    # Check if it's a class and is a subclass of BaseEvaluator (but not BaseEvaluator itself)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseEvaluator)
                        and attr is not BaseEvaluator
                    ):
                        try:
                            evaluator_inst = attr()
                            self.evaluators.append(evaluator_inst)
                            logger.info(
                                f"EvaluationManager: Loaded plugin '{evaluator_inst.name}' from {name}"
                            )
                        except Exception as e:
                            logger.error(
                                f"EvaluationManager: Failed to instantiate {attr_name} from {name}: {e}"
                            )
        except Exception as e:
            logger.error(f"EvaluationManager: Plugin discovery failed: {e}")

    def get_evaluator(self, name: str) -> Optional[BaseEvaluator]:
        """Returns a loaded evaluator by its name."""
        for ev in self.evaluators:
            if ev.name == name:
                return ev
        return None

    async def evaluate_all(self, code: str, language: str, **kwargs) -> Dict[str, Any]:
        """
        Runs all applicable evaluators and merges results.
        """
        lang = language.lower()
        results: Dict[str, EvaluationResult] = {}

        # 1. Critical Step: Structural check first
        structural = self.get_evaluator("structural")
        if structural:
            struct_res = await structural.evaluate(code, lang)
            if struct_res.score == 0:
                return {
                    "score": 0.0,
                    "reason": f"Critical Failure: {struct_res.reason}",
                    "details": {"structural": struct_res},
                }
            results["structural"] = struct_res
        else:
            logger.warning(
                "EvaluationManager: StructuralEvaluator not found in plugins."
            )

        # 2. Run others (AI and Static)
        tasks = []
        eval_map = {}

        for ev in self.evaluators:
            if ev.name == "structural":
                continue
            tasks.append(ev.evaluate(code, lang, **kwargs))
            eval_map[len(tasks) - 1] = ev.name

        eval_outputs = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(eval_outputs):
            name = eval_map[i]
            if isinstance(res, Exception):
                logger.error(f"EvaluationManager: Evaluator '{name}' failed: {res}")
                results[name] = EvaluationResult(
                    score=0.0, reason=f"Evaluator error: {res}"
                )
            else:
                results[name] = res

        # 3. Final Scoring Logic (Refined weighted logic)
        final_score = 0.0
        reasons = []

        ai_res = results.get("ai_gate")
        python_static_res = results.get("python_static")
        ruff_res = results.get("ruff")
        eslint_res = results.get("eslint")

        # Basic Quality Gate: Block on Syntax Errors for Python
        if lang == "python" and python_static_res and python_static_res.score == 0:
            return {
                "score": 0.0,
                "reason": f"Critical Quality Failure: {python_static_res.reason}",
                "details": {
                    k: {"score": v.score, "reason": v.reason} for k, v in results.items()
                },
            }

        if lang == "python":
            # 40% AI, 30% Ruff, 30% AST Static
            parts = []
            if ai_res and ai_res.score > 0:
                parts.append((ai_res.score, 0.40, f"AI: {ai_res.reason}"))

            if ruff_res and ruff_res.score < 100:  # Only if Ruff was able to run
                parts.append((ruff_res.score, 0.30, f"Ruff: {ruff_res.reason}"))
            else:
                # If Ruff skipped or not found, redistribute weight to static
                if python_static_res:
                    static_weight = 0.60
                    parts.append(
                        (
                            python_static_res.score,
                            static_weight,
                            f"Static (AST): {python_static_res.reason}",
                        )
                    )
                elif ai_res:
                    pass

            # Re-calculate with normalized weights if some failed
            total_weight = sum(p[1] for p in parts)
            if total_weight > 0:
                for score, weight, reason in parts:
                    final_score += score * (weight / total_weight)
                    reasons.append(reason)
            else:
                final_score = 0.0
                reasons.append("All Python evaluations failed.")

        elif lang in ["javascript", "typescript", "javascriptreact", "typescriptreact"]:
            # 60% AI, 40% ESLint
            if eslint_res and eslint_res.score < 100:
                if ai_res and ai_res.score > 0:
                    final_score = (ai_res.score * 0.6) + (eslint_res.score * 0.4)
                    reasons.append(f"AI: {ai_res.reason}")
                    reasons.append(f"ESLint: {eslint_res.reason}")
                else:
                    final_score = eslint_res.score
                    reasons.append(f"AI failed. ESLint: {eslint_res.reason}")
            else:
                if ai_res:
                    final_score = ai_res.score
                    reasons.append(f"AI: {ai_res.reason}")
                else:
                    final_score = 0
                    reasons.append("All JS/TS evaluations failed.")
        else:
            # 100% LLM for other languages
            if ai_res:
                final_score = ai_res.score
                reasons.append(f"AI ({lang}): {ai_res.reason}")
            else:
                final_score = 0
                reasons.append(
                    "AI Evaluation failed and no static analyzer for this language."
                )

        return {
            "score": final_score,
            "reason": " | ".join(reasons),
            "details": {
                k: {"score": v.score, "reason": v.reason} for k, v in results.items()
            },
        }
