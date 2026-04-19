import os

from google import genai
from google.genai import errors


class NovelLLMClient:
    """
    小説執筆支援システム向けの堅牢なLLMクライアント。
    Google Gemini APIを使用し、マルチモデルフォールバック、プリセット解決、
    非同期（aio）呼び出し、および構造化出力（JSON Schema）をサポートします。
    """

    def __init__(self, api_key: str | None = None, presets: dict | None = None):
        self.client = genai.Client(api_key=api_key or os.getenv("GOOGLE_API_KEY"))
        self.presets = presets or {
            "quality_priority": ["gemini-2.0-pro-exp-02-05", "gemini-2.0-flash"],
            "resource_priority": ["gemini-2.0-flash", "gemini-2.0-flash-lite"],
            "embedding": ["gemini-embedding-001"],
        }

    def resolve_models(self, model_input: str | list[str]) -> list[str]:
        if isinstance(model_input, list):
            resolved = []
            for m in model_input:
                resolved.extend(self.presets.get(m, [m]))
            return resolved
        return self.presets.get(model_input, [model_input])

    async def generate_content(
        self, model: str | list[str], contents: str | list, config: dict | None = None, **kwargs
    ):
        """フォールバックロジック付き非同期生成。Structured Outputをサポート。"""
        models = self.resolve_models(model)
        last_error = None
        generation_config = config or {}

        for m in models:
            try:
                response = await self.client.aio.models.generate_content(
                    model=m, contents=contents, config=generation_config, **kwargs
                )
                return response
            except errors.ClientError as e:
                last_error = e
                error_str = str(e).lower()
                if any(code in error_str for code in ["429", "500", "503"]):
                    continue
                break  # Prompt/Auth errors should not fallback
            except Exception as e:
                last_error = e
                continue
        raise last_error

    async def embed_content(self, model: str | list[str], contents: str | list, **kwargs):
        """フォールバックロジック付き非同期埋め込み。"""
        models = self.resolve_models(model)
        last_error = None
        for m in models:
            try:
                return await self.client.aio.models.embed_content(
                    model=m, contents=contents, **kwargs
                )
            except Exception as e:
                last_error = e
                continue
        raise last_error
