import logging

from core.config import GEMINI_API_KEY
from core.consolidation import LogicIntelligence

from ..base import BaseEvaluator, EvaluationResult

logger = logging.getLogger(__name__)


class AIGateEvaluator(BaseEvaluator):
    """
    Evaluates code quality using LLM-based logic gate.
    """

    @property
    def name(self) -> str:
        return "ai_gate"

    def __init__(self, api_key: str = GEMINI_API_KEY, intel: LogicIntelligence | None = None):
        self.intel = intel or LogicIntelligence(api_key)

    async def evaluate(self, code: str, language: str, **kwargs) -> EvaluationResult:
        try:
            test_code = kwargs.get("test_code", "")
            quality = await self.intel.evaluate_quality(code, test_code=test_code)
            score = float(quality.get("score", 0))
            reason = quality.get("reason", "No reason provided by AI.")
            return EvaluationResult(score=score, reason=reason)
        except Exception as e:
            logger.error(f"AIGateEvaluator: AI Evaluation failed: {e}")
            # We don't return 0 here because it might be a transient AI error.
            # The manager will handle the fallback.
            raise
