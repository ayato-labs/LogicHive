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
        test_code = kwargs.get("test_code", "")
        
        # 0. Strict check for non-draft assets
        is_draft = "[AI_DRAFT]" in (kwargs.get("description", "") or "") or "[AI-DRAFT]" in (kwargs.get("description", "") or "")
        
        # If it's not a draft and has NO test code, it's a 'Sophistry' attempt or incomplete asset.
        if not is_draft and not test_code:
            return {
                "score": 0.0,
                "reason": "Security/Stability Failure: Non-draft assets MUST have meaningful test code to be VERIFIED.",
                "details": {"system": "Rigor Gate"},
            }

        # 1. Critical Step: Structural check first
        structural = self.get_evaluator("structural")
        if structural:
            struct_res = await structural.evaluate(code, lang, **kwargs)
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

        # 2. Run others (AI, Static, Runtime)
        tasks = []
        eval_map = {}

        for ev in self.evaluators:
            if ev.name == "structural":
                continue
            # Pass everything in kwargs (including test_code)
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
        runtime_res = results.get("runtime")

        # 4. Weighted Calculation
        # Weights: AI (30%), Static/Ruff (30%), Runtime (40%)
        parts = []
        
        # AI Gate (30%)
        if ai_res:
            parts.append((ai_res.score, 0.30, f"AI/Rigor: {ai_res.reason}"))
            
        # Static Analysis (30%)
        if lang == "python":
            if ruff_res and ruff_res.score < 100:
                parts.append((ruff_res.score, 0.30, f"Ruff: {ruff_res.reason}"))
            elif python_static_res:
                parts.append((python_static_res.score, 0.30, f"Static: {python_static_res.reason}"))
        elif eslint_res:
            parts.append((eslint_res.score, 0.30, f"ESLint: {eslint_res.reason}"))

        # Runtime Verification (40%) - THE MOST CRITICAL
        if runtime_res:
            runtime_score = runtime_res.score
            
            # HARD BLOCK: If it's NOT a draft and tests fail with logic error (score 0), 
            # we force final score to 0 to trigger researcher's logic.
            if runtime_score == 0 and not is_draft:
                return {
                    "score": 0.0,
                    "reason": f"Critical Logic Failure (Verified Asset): {runtime_res.reason}",
                    "details": {k: {"score": v.score, "reason": v.reason} for k, v in results.items()},
                }
                
            parts.append((runtime_score, 0.40, f"Runtime: {runtime_res.reason}"))

        # Normalized weight calculation
        total_weight = sum(p[1] for p in parts)
        if total_weight > 0:
            raw_final = 0.0
            for score, weight, reason in parts:
                raw_final += score * (weight / total_weight)
                reasons.append(reason)
            
            # ABSOLUTE RIGOR ENFORCEMENT:
            if ai_res:
                ai_score = ai_res.score
                
                # 1. KILL-SWITCH: If AI identifies 'Quality Theater' or 'Hollow Logic' (Score < 30)
                if ai_score < 30:
                    final_score = 0.0
                    reasons.insert(0, "CRITICAL REJECTION: AI Forensic Auditor identified 'Quality Theater' or Hollow Logic. Asset discarded.")
                
                # 2. VETO POWER: If AI score is below 70, the overall asset CANNOT be 'Verified'.
                # We cap the final score at the AI score to prevent 'Sophistry' by averaging.
                elif ai_score < 70:
                    final_score = min(raw_final, ai_score)
                    reasons.insert(0, f"VETO: AI Auditor expressed doubt about asset rigor (Score: {ai_score}). Overall score capped.")
                else:
                    final_score = raw_final
            else:
                final_score = raw_final
        else:
            final_score = 0.0
            reasons.append("No applicable evaluators succeeded.")

        return {
            "score": final_score,
            "reason": " | ".join(reasons),
            "details": {
                k: {"score": v.score, "reason": v.reason} for k, v in results.items()
            },
        }
