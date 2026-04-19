import json
import logging
import re

from google import genai


class GeminiService:
    """
    Google Gen AI SDK (google-genai) wrapper for multi-model fallback and structured output.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=self.api_key)

    async def _call_api_async(
        self, model_names, prompt, is_json_output=False, response_schema=None
    ):
        if isinstance(model_names, str):
            model_names = [model_names]
        last_exception = None
        for model_name in model_names:
            try:
                config = {}
                is_gemini_model = model_name.startswith("gemini")
                if response_schema and is_gemini_model:
                    config["response_mime_type"] = "application/json"
                    config["response_schema"] = response_schema
                elif is_json_output and is_gemini_model:
                    config["response_mime_type"] = "application/json"
                response = await self.client.aio.models.generate_content(
                    model=model_name, contents=prompt, config=config
                )
                if response.text:
                    if response_schema or is_json_output:
                        return self._parse_json_response(response.text.strip(), "Gemini API")
                    return response.text.strip()
                raise Exception(f"Empty response from {model_name}")
            except Exception as e:
                last_exception = e
                logging.warning(f"Gemini Request Failed for {model_name}: {e}")
                continue
        raise (last_exception or Exception("Gemini Request Failed All Models"))

    def _parse_json_response(self, text, prefix):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            cleaned = text.strip()
            match = re.search(r"```json\s*([\s\S]+?)\s*```", cleaned) or re.search(
                r"```\s*([\s\S]+?)\s*```", cleaned
            )
            if match:
                cleaned = match.group(1)
            try:
                return json.loads(cleaned)
            except:
                return {}
