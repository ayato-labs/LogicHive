import logging

from core.config import (
    EMBEDDING_MODEL_ID,
    GEMINI_API_KEY,
)

# Suppress verbose third-party logging
logging.getLogger("google.genai").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class GeminiEmbeddingService:
    """
    Cloud Embedding Service using Google Gemini (Explicitly 768D).
    """

    def __init__(self):
        self.model_name = EMBEDDING_MODEL_ID
        self._api_key = GEMINI_API_KEY
        self._client = None

    def _ensure_initialized(self):
        if self._client:
            return

        if not self._api_key:
            logger.error("GeminiEmbeddingService: API Key is missing. Check settings.")
            return

        try:
            # Use the new Google GenAI SDK (google-genai)
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
            logger.info("GeminiEmbeddingService: Initialized successfully.")
        except Exception as e:
            logger.error(f"GeminiEmbeddingService: Initialization Failed: {e}")

    def get_embedding(self, text: str, is_query: bool = False) -> list[float]:
        self._ensure_initialized()
        if not self._client:
            return [0.0] * 768

        try:
            # Explicitly set output_dimensionality to 768 to match Supabase schema
            result = self._client.models.embed_content(
                model=self.model_name,
                contents=text,
                config={
                    "task_type": "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT",
                    "output_dimensionality": 768,
                },
            )
            # Result contains 'embeddings', a list of values
            vector = result.embeddings[0].values
            return list(vector)

        except Exception as e:
            logger.error(f"GeminiEmbeddingService: Inference Failed - {e}")
            return [0.0] * 768

    def get_model_info(self) -> dict:
        return {
            "model_name": self.model_name,
            "dimension": 768,
            "device": "cloud",
        }


# Singleton Instance
# NOTE: Per system architecture, gemini-embedding-001 is the mandatory one-choice for embeddings.
embedding_service = GeminiEmbeddingService()
