import logging
import asyncio
from typing import List, Dict, Any
from .base import BaseEvaluator, EvaluationResult
from .static_analysis import StructuralEvaluator, PythonStaticEvaluator
from .ai_gate import AIGateEvaluator

logger = logging.getLogger(__name__)

class EvaluationManager:
    """
    Coordinates multiple evaluators to determine the final quality score.
    """
    def __init__(self):
        self.evaluators: List[BaseEvaluator] = [
            StructuralEvaluator(),
            PythonStaticEvaluator(),
            AIGateEvaluator()
        ]

    async def evaluate_all(self, code: str, language: str, **kwargs) -> Dict[str, Any]:
        """
        Runs all applicable evaluators and merges results.
        """
        lang = language.lower()
        results: Dict[str, EvaluationResult] = {}
        
        # 1. Critical Step: Structural check first
        structural = StructuralEvaluator()
        struct_res = await structural.evaluate(code, lang)
        if struct_res.score == 0:
            return {
                "score": 0.0,
                "reason": f"Critical Failure: {struct_res.reason}",
                "details": {"structural": struct_res}
            }
        results["structural"] = struct_res

        # 2. Run others (AI and Static)
        # Note: In a production plugin system, we'd filter by language here.
        tasks = []
        eval_map = {}
        
        for ev in self.evaluators:
            if ev.name == "structural":
                continue
            tasks.append(ev.evaluate(code, lang, **kwargs))
            eval_map[len(tasks)-1] = ev.name

        eval_outputs = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, res in enumerate(eval_outputs):
            name = eval_map[i]
            if isinstance(res, Exception):
                logger.error(f"EvaluationManager: Evaluator '{name}' failed: {res}")
                results[name] = EvaluationResult(score=0.0, reason=f"Evaluator error: {res}")
            else:
                results[name] = res

        # 3. Final Scoring Logic (Refined weighted logic)
        final_score = 0.0
        reasons = []
        
        ai_res = results.get("ai_gate")
        static_res = results.get("python_static")

        if lang == "python":
            # 50/50 split between AI and Static
            # Fallback if AI failed (score 0 due to exception)
            if ai_res and ai_res.score > 0:
                final_score = (ai_res.score * 0.5) + (static_res.score * 0.5)
                reasons.append(f"AI: {ai_res.reason}")
                reasons.append(f"Static: {static_res.reason}")
            else:
                final_score = static_res.score
                reasons.append("AI Evaluation skipped/failed. Falling back to static analysis.")
                reasons.append(f"Static: {static_res.reason}")
        else:
            # 100% LLM for other languages
            if ai_res:
                final_score = ai_res.score
                reasons.append(f"AI ({lang}): {ai_res.reason}")
            else:
                final_score = 0
                reasons.append("AI Evaluation failed and no static analyzer for this language.")

        return {
            "score": final_score,
            "reason": " | ".join(reasons),
            "details": {k: {"score": v.score, "reason": v.reason} for k, v in results.items()}
        }
