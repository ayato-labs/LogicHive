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
)

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
                config=types.EmbedContentConfig(output_dimensionality=768),
            )
            return response.embeddings[0].values
        except Exception as e:
            logger.error(f"Consolidation: Gemini Embedding (001) failed: {e}")
            return []

    async def optimize_metadata(
        self, code: str, current_description: str = "", current_tags: List[str] = []
    ) -> Dict[str, Any]:
        """Uses AI into generating a high-density technical whitepaper for RAG optimization."""
        prompt = (
            f"You are a technical documentation architect for LogicHive.\n"
            f"Code:\n{code}\n\n"
            f"Current Description: {current_description}\n"
            f"Current Tags: {current_tags}\n\n"
            f"Task: Generate a high-quality technical specification in English.\n"
            f"The documentation MUST follow this structure:\n"
            f"1. HIGH-LEVEL PURPOSE: What problem does this solve?\n"
            f"2. TECHNICAL LOGIC FLOW: Step-by-step breakdown of the internal algorithm.\n"
            f"3. API SPECIFICATION: Detailed description of arguments, types, and return values.\n"
            f"4. EDGE CASES & CONSTRAINTS: Potential failure points or performance notes.\n"
            f"5. USAGE SCENARIO: When should a developer choose this logic?\n\n"
            f"Also generate 8-12 highly relevant tags.\n"
            f"CONTEXT: This is for a RAG system. Focus on semantic density and technical precision.\n"
            f"IMPORTANT: The response must be in English. Respond ONLY in JSON format with keys 'description' and 'tags'."
        )

        provider = await self._get_optimal_provider()

        if provider == "gemini":
            try:
                if not self.gemini_client:
                    return {"description": current_description, "tags": current_tags}

                # Gemma models often don't support response_mime_type="application/json"
                use_json_mode = "gemma" not in self.model_id.lower()
                
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
                # Extremely robust JSON extraction: find the first '{' and last '}'
                try:
                    start_idx = text.find('{')
                    end_idx = text.rfind('}')
                    if start_idx != -1 and end_idx != -1:
                        json_str = text[start_idx:end_idx+1]
                        data = json.loads(json_str)
                    else:
                        raise ValueError("No JSON object found in response.")
                        
                    return {
                        "description": data.get("description", current_description),
                        "tags": data.get("tags", current_tags),
                    }
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Consolidation: Failed to parse JSON from {self.model_id}. Raw text: {text[:500]}... Error: {e}")
                    return {"description": current_description, "tags": current_tags}
            except Exception as e:
                logger.warning(
                    f"Consolidation: Gemini Metadata optimization failed for {self.model_id}: {e}"
                )
                return {"description": current_description, "tags": current_tags}

        elif provider == "ollama":
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": self.ollama_model,
                            "prompt": prompt + "\nRespond ONLY with JSON.",
                            "stream": False,
                            "format": "json",
                        },
                    )
                    if resp.status_code == 200:
                        data = json.loads(resp.json().get("response", "{}"))
                        return {
                            "description": data.get("description", current_description),
                            "tags": data.get("tags", current_tags),
                        }
                    return {"description": current_description, "tags": current_tags}
            except Exception as e:
                logger.warning(
                    f"Consolidation: Ollama Metadata optimization failed: {e}"
                )
                return {"description": current_description, "tags": current_tags}

        return {"description": current_description, "tags": current_tags}

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
