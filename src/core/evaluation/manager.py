import asyncio
import importlib
import importlib.util
import logging
import os
import pkgutil
from typing import Any

from .base import BaseEvaluator, EvaluationResult

logger = logging.getLogger(__name__)


class EvaluationManager:
    """
    Coordinates multiple evaluators to determine the final quality score.
    Now supports dynamic plugin loading from the .plugins package.
    """

    def __init__(self):
        self.evaluators: list[BaseEvaluator] = []
        self._load_plugins()

    def _load_plugins(self):
        """
        Dynamically discovers and instantiates all BaseEvaluator subclasses.
        Uses both package-based and filesystem-based discovery for maximum reliability.
        """
        try:
            plugins_dir = os.path.join(os.path.dirname(__file__), "plugins")
            if not os.path.exists(plugins_dir):
                logger.error(f"EvaluationManager: Plugins directory not found at {plugins_dir}")
                return

            # Collect all potential module candidates
            modules = []

            # 1. Try package-based discovery (cleanest)
            package_names = [
                f"{__package__}.plugins" if __package__ else None,
                "core.evaluation.plugins",
                "src.core.evaluation.plugins"
            ]

            for pkg_name in [p for p in package_names if p]:
                try:
                    pkg = importlib.import_module(pkg_name)
                    for loader, name, is_pkg in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
                        try:
                            modules.append(importlib.import_module(name))
                        except ImportError:
                            continue
                    if modules:
                        break # Successfully loaded via package
                except ImportError:
                    continue

            # 2. Filesystem fallback if package discovery didn't find everything
            if not modules:
                for filename in os.listdir(plugins_dir):
                    if filename.endswith(".py") and filename != "__init__.py":
                        module_name = filename[:-3]
                        file_path = os.path.join(plugins_dir, filename)
                        try:
                            spec = importlib.util.spec_from_file_location(module_name, file_path)
                            if spec and spec.loader:
                                mod = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(mod)
                                modules.append(mod)
                        except Exception as e:
                            logger.error(f"EvaluationManager: Failed to load {filename} via fallback: {e}")

            # 3. Instantiate evaluators from discovered modules
            for module in modules:
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseEvaluator)
                        and attr is not BaseEvaluator
                    ):
                        try:
                            inst = attr()
                            if not any(e.name == inst.name for e in self.evaluators):
                                self.evaluators.append(inst)
                                logger.info(f"EvaluationManager: Loaded plugin '{inst.name}'")
                        except Exception as e:
                            logger.error(f"EvaluationManager: Failed to instantiate {attr_name}: {e}")

        except Exception as e:
            logger.error(f"EvaluationManager: Plugin discovery process failed: {e}")

    def get_evaluator(self, name: str) -> BaseEvaluator | None:
        """Returns a loaded evaluator by its name."""
        for ev in self.evaluators:
            if ev.name == name:
                return ev
        return None

    async def evaluate_all(self, code: str, language: str, **kwargs) -> dict[str, Any]:
        """
        Runs all applicable evaluators and merges results.
        """
        lang = language.lower()
        results: dict[str, EvaluationResult] = {}
        test_code = kwargs.get("test_code", "")

        # 0. Strict check for non-draft assets
        desc = (kwargs.get("description") or "").upper()
        # Support both flag and description keywords (DRAFT, AI_DRAFT, AI-DRAFT)
        is_draft = (
            kwargs.get("is_draft", False)
            or "DRAFT" in desc
            or "AI_DRAFT" in desc
            or "AI-DRAFT" in desc
        )

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

        # 3. Final Scoring Logic (Hybrid Architecture: Fact over Opinion)
        final_score = 0.0
        reasons = []

        ai_res = results.get("ai_gate")
        det_res = results.get("deterministic")
        runtime_res = results.get("runtime")
        
        # New Rigour-inspired evaluators
        sec_static = results.get("security_static")
        dep_vouch = results.get("dependency_vouch")
        metrics_res = results.get("metrics_gate")
        
        # Fallback static evaluators
        python_static_res = results.get("python_static")
        ruff_res = results.get("ruff")
        eslint_res = results.get("eslint")

        # --- RIGOUR IMMUNE SYSTEM: CRITICAL FILTERS ---
        # If static security check finds high-risk flaws (score < 60), reject immediately.
        if sec_static and sec_static.score < 60:
            return {
                "score": 0.0,
                "reason": f"SECURITY REJECTION: {sec_static.reason}",
                "details": {k: {"score": v.score, "reason": v.reason} for k, v in results.items()},
            }
        
        # If dependency check finds hallucinations, it's a 'garbage' logic. reject.
        if dep_vouch and dep_vouch.score < 70:
            return {
                "score": 0.0,
                "reason": f"DEPENDENCY REJECTION: {dep_vouch.reason}",
                "details": {k: {"score": v.score, "reason": v.reason} for k, v in results.items()},
            }

        # 4. Weighted Calculation
        # Weights: Deterministic (30%), Runtime (30%), Static/Security (20%), AI (15%), Metrics (5%)
        parts = []

        # A. Deterministic Layer (30%) - THE TRUTH FOUNDATION
        if det_res:
            det_score = det_res.score
            if det_score == 0:
                return {
                    "score": 0.0,
                    "reason": f"DETERMINISTIC REJECTION: {det_res.reason}",
                    "details": {k: {"score": v.score, "reason": v.reason} for k, v in results.items()},
                }
            parts.append((det_score, 0.30, f"Facts: {det_res.reason}"))

        # B. Runtime Verification (30%)
        if runtime_res:
            runtime_score = runtime_res.score
            if runtime_score == 0 and not is_draft:
                return {
                    "score": 0.0,
                    "reason": f"Critical Logic Failure (Verified Asset): {runtime_res.reason}",
                    "details": {k: {"score": v.score, "reason": v.reason} for k, v in results.items()},
                }
            parts.append((runtime_score, 0.30, f"Runtime: {runtime_res.reason}"))

        # C. Static/Security Analysis (20%)
        static_scores = []
        if sec_static: static_scores.append(sec_static.score)
        if dep_vouch: static_scores.append(dep_vouch.score)
        
        if lang == "python":
            if ruff_res: static_scores.append(ruff_res.score)
            elif python_static_res: static_scores.append(python_static_res.score)
        elif eslint_res:
            static_scores.append(eslint_res.score)
        
        if static_scores:
            avg_static = sum(static_scores) / len(static_scores)
            parts.append((avg_static, 0.20, f"Rigour Static: Security/Dependency verified (Avg={avg_static:.1f})"))

        # D. AI Gate (15%) - THE AUDITOR'S OPINION
        if ai_res:
            parts.append((ai_res.score, 0.15, f"AI Opinion: {ai_res.reason}"))

        # E. Metrics/Refactoring Gate (5%)
        if metrics_res:
            parts.append((metrics_res.score, 0.05, f"Maintainability: {metrics_res.reason}"))

        # Normalized weight calculation
        total_weight = sum(p[1] for p in parts)
        if total_weight > 0:
            raw_final = 0.0
            for score, weight, reason in parts:
                raw_final += score * (weight / total_weight)
                reasons.append(reason)

            # ABSOLUTE RIGOR ENFORCEMENT (Veto Layer):
            if ai_res:
                ai_score = ai_res.score
                if ai_score < 30:
                    final_score = 0.0
                    reasons.insert(0, "VETO: AI Auditor identified 'Quality Theater' - Opinion confirmed rejection.")
                elif ai_score < 70:
                    final_score = min(raw_final, ai_score)
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
