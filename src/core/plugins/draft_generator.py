import logging
from typing import List, Dict, Any, Optional
from core.consolidation import LogicIntelligence
from core.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)


class DraftGenerator:
    """
    Synthesizes draft code when no high-similarity match is found in the vault.
    Uses existing vault patterns as context to maintain consistency.
    """

    def __init__(self, intel: Optional[LogicIntelligence] = None):
        self.intel = intel or LogicIntelligence(GEMINI_API_KEY)

    async def generate_draft(
        self,
        query: str,
        context_results: List[Dict[str, Any]],
        language: str = "python",
    ) -> Dict[str, Any]:
        """
        Generates a functional draft based on the user query and nearby context.
        """
        if not context_results:
            logger.info("DraftGenerator: No context available for synthesis.")
            context_str = "No existing patterns found in the vault."
        else:
            # Format context for the LLM
            context_snippets = []
            for res in context_results[:3]:  # Use top 3 as examples
                context_snippets.append(
                    f"NAME: {res['name']}\nDESC: {res['description']}\nCODE:\n{res['code']}\n"
                )
            context_str = "\n---\n".join(context_snippets)

        prompt = (
            f"You are the LogicHive Draft Assistant. Your goal is to synthesize a high-quality, reusable code draft.\n"
            f"User Query/Target: {query}\n"
            f"Language: {language}\n\n"
            f"Below are some similar patterns from the existing LogicHive vault. \n"
            f"Follow the coding style, naming conventions, and robustness patterns seen here:\n"
            f"{context_str}\n\n"
            f"Task: Generate a draft implementation that solves the User Query.\n"
            f"REQUIREMENTS:\n"
            f"1. Respond ONLY with a JSON object containing keys: 'name', 'code', 'description', 'tags', 'dependencies'.\n"
            f"2. The code should be functional and follow the patterns provided.\n"
            f"3. Mark this clearly as a DRAFT in the description.\n"
            f"4. Focus on atomicity and reusability."
        )

        try:
            res = await self.intel._call_llm_async(prompt, use_json=True)
            if not res or "code" not in res:
                return {}

            # Ensure it is marked as draft
            res["is_draft"] = True
            res["provenance"] = "LogicHive Auto-Draft"
            if "description" in res:
                res["description"] = f"[AI-DRAFT] {res['description']}"
            else:
                res["description"] = f"[AI-DRAFT] Draft implementation for {query}"

            # Force language if missing
            if "language" not in res:
                res["language"] = language

            return res
        except Exception as e:
            logger.error(f"DraftGenerator: Failed to synthesize draft: {e}")
            return {}
