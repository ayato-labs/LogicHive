import logging
import json
from typing import List, Optional, Dict, Any
import httpx
from google import genai
from google.genai import types

from core.config import (
    MODEL_TYPE,
    GEMINI_API_KEY,
    OLLAMA_URL,
    OLLAMA_MODEL,
    EMBEDDING_MODEL_ID,
    VECTOR_DIMENSION,
)
from core.exceptions import AIProviderError

logger = logging.getLogger(__name__)


class LogicIntelligence:
    """
    LogicHub Intelligence Engine.
    Handles embedding generation and quality evaluation using BYOK models (Gemini or Ollama).
    """

    async def _get_optimal_provider(self):
        """Internal helper to decide which provider to use for generation."""
        # Prefer Gemini if key is available, as it's required for high-quality metadata enrichment
        if self.gemini_client:
            return "gemini"
        return self.provider

    def __init__(self, api_key: Optional[str] = None):
        self.provider = MODEL_TYPE.lower()
        self.gemini_key = api_key or GEMINI_API_KEY
        self.embedding_model = EMBEDDING_MODEL_ID

        # Always initialize Gemini client for Embeddings (BYOK requirement)
        if self.gemini_key:
            self.gemini_client = genai.Client(api_key=self.gemini_key)
        else:
            self.gemini_client = None

        # For generation tasks, we dynamically choose based on availability
        from core.config import GEMINI_MODEL

        self.model_id = GEMINI_MODEL
        self.ollama_url = OLLAMA_URL
        self.ollama_model = OLLAMA_MODEL

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generates embedding for the given text.
        NOTE: Per system architecture, this project uses gemini-embedding-001 exclusively.
        Input is truncated to stay within the 2,048 token limit.
        """
        if not self.gemini_client:
            logger.warning("Consolidation: Gemini API Key missing for embeddings.")
            return []

        # Heuristic truncation: 7,000 chars is roughly 1750-2000 tokens
        safe_text = text[:7000]

        try:
            response = self.gemini_client.models.embed_content(
                model=self.embedding_model,
                contents=[safe_text],
                config=types.EmbedContentConfig(output_dimensionality=VECTOR_DIMENSION),
            )
            return response.embeddings[0].values
        except Exception as e:
            logger.error(f"Consolidation: Gemini Embedding (001) failed: {e}")
            return []

    async def _call_llm_async(self, prompt: str, use_json: bool = True) -> Any:
        """
        Internal helper to route LLM calls to Gemini or Ollama and handle JSON extraction.
        """
        provider = await self._get_optimal_provider()

        if provider == "gemini":
            if not self.gemini_client:
                return {} if use_json else ""

            try:
                # Gemma models often don't support response_mime_type="application/json"
                use_json_mode = use_json and "gemma" not in self.model_id.lower()

                config = (
                    types.GenerateContentConfig(response_mime_type="application/json")
                    if use_json_mode
                    else None
                )

                response = self.gemini_client.models.generate_content(
                    model=self.model_id,
                    contents=[prompt],
                    config=config,
                )
                text = response.text

                if not use_json:
                    return text.strip()

                # Robust JSON extraction
                try:
                    start_idx = text.find("{")
                    end_idx = text.rfind("}")
                    if start_idx != -1 and end_idx != -1:
                        json_str = text[start_idx : end_idx + 1]
                        parsed = json.loads(json_str)
                        if isinstance(parsed, list):
                            return (
                                parsed[0]
                                if len(parsed) > 0 and isinstance(parsed[0], dict)
                                else {}
                            )
                        return parsed if isinstance(parsed, dict) else {}
                    return {}
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(
                        f"Consolidation: Failed to parse JSON from {self.model_id}: {e}. Raw content: {text[:200]}..."
                    )
                    return {}
            except Exception as e:
                logger.error(f"Consolidation: Gemini call failed: {e}")
                raise AIProviderError(f"Gemini generation failed: {e}")

        elif provider == "ollama":
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": self.ollama_model,
                            "prompt": prompt
                            + ("\nRespond ONLY with JSON." if use_json else ""),
                            "stream": False,
                            "format": "json" if use_json else None,
                        },
                    )
                    if resp.status_code != 200:
                        raise AIProviderError(
                            f"Ollama returned status {resp.status_code}"
                        )

                    raw_text = resp.json().get("response", "")
                    if not use_json:
                        return raw_text.strip()
                    return json.loads(raw_text)
            except Exception as e:
                logger.error(f"Consolidation: Ollama call failed: {e}")
                raise AIProviderError(f"Ollama generation failed: {e}")

        raise AIProviderError("No valid AI provider available.")

    async def evaluate_quality(self, code: str) -> Dict[str, Any]:
        """
        Evaluates the quality of the given code asset.
        LogicHive's "Quality Gate" ensures only high-quality, reusable logic is saved.
        """
        prompt = (
            f"You are a Senior Software Architect and strict quality gatekeeper for LogicHive.\n"
            f"Code to evaluate:\n{code}\n\n"
            f"Task: Evaluate if this code is a high-quality, reusable, and atomic logic asset.\n"
            f"CRITICAL REQUIREMENT: Conduct a virtual compilation/linting check.\n"
            f"1. SYNTAX CHECK: Are there any syntax errors, missing brackets, or obvious reference errors for the specified language?\n"
            f"   If it is NOT runnable or contains syntax errors, you MUST return a score of 0.\n"
            f"2. ATOMICITY: Does it solve ONE specific problem well?\n"
            f"3. REUSABILITY: Is it free from project-specific hardcoded strings or dependencies?\n"
            f"4. READABILITY: Is the logic clear and well-structured?\n\n"
            f"Scoring (Integer 0-100):\n"
            f"- 0: Syntax Error, Missing brackets, or Garbage (REJECT IMMEDIATELY)\n"
            f"  If the code is NOT runnable or contains syntax errors, you MUST return exactly 0.\n"
            f"- 1-40: Poor quality or trivial logic (Reject)\n"
            f"- 41-69: Needs improvement (Reject)\n"
            f"- 70-100: High quality (Accept)\n\n"
            f"IMPORTANT: Respond ONLY in JSON format with keys 'score' (int) and 'reason' (string explaining why)."
        )

        try:
            res = await self._call_llm_async(prompt, use_json=True)
        except AIProviderError as e:
            logger.error(f"Quality Gate: AI Provider failed during evaluation: {e}")
            # Fallback for transient AI issues if needed, or re-raise
            raise

        # Robust Score Coercion
        raw_score = res.get("score", 0)
        try:
            if isinstance(raw_score, (int, float)):
                score = int(raw_score)
            elif isinstance(raw_score, str):
                # Handle cases where LLM might return "85"
                score = int(float(raw_score))
            elif isinstance(raw_score, dict):
                # Fallback: find the first numeric value in the dict
                score = int(
                    next(
                        (v for v in raw_score.values() if isinstance(v, (int, float))),
                        0,
                    )
                )
            else:
                score = 0
        except (ValueError, TypeError, StopIteration) as e:
            logger.error(
                f"Consolidation: Score coercion failed for input '{raw_score}': {e}"
            )
            score = 0

        return {
            "score": score,
            "reason": res.get("reason", "Failed to obtain evaluation reason."),
        }

    async def expand_query(self, user_query: str) -> str:
        """Expands a natural language user query into a dense technical search document."""
        prompt = (
            f"You are a technical search architect for LogicHive.\n"
            f"User Query: {user_query}\n\n"
            f"Task: Expand this query into technical keywords and implementation patterns in English.\n"
            f"Focus on semantic density to maximize RAG retrieval accuracy.\n"
            f"IMPORTANT: Respond ONLY with the expanded keywords. No preamble."
        )

        expanded = await self._call_llm_async(prompt, use_json=False)
        return expanded or user_query

    def construct_search_document(
        self, name: str, description: str, tags: List[str], code: str
    ) -> str:
        """
        Constructs a structured document for embedding to maximize RAG relevance.
        Prioritizes semantic metadata while preserving logic context from the code.
        """
        # Document Structure: Title -> Semantic Spec -> Tags -> Implementation
        tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
        doc = (
            f"LOGIC ASSET: {name}\n"
            f"TECHNICAL SPECIFICATION:\n{description}\n"
            f"TAGS: {tags_str}\n"
            f"--- IMPLEMENTATION DETALS ---\n"
            f"{code}"
        )
        # Note: generate_embedding will handle the final 7,000 char (2048 token) truncation.
        return doc
