import json
import os
import sys

from dotenv import load_dotenv
from google import genai


def get_client():
    """Helper to initialize and return the genai Client with robust .env lookup."""
    # Prioritize local .env in the project directory
    load_dotenv(".env", override=True)

    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        api_key = api_key.strip('"').strip("'")

    if not api_key:
        # Fallback to parent directory (common in multi-layer projects)
        dotenv_path = os.path.join(os.getcwd(), "..", ".env")
        load_dotenv(dotenv_path)
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            api_key = api_key.strip('"').strip("'")

    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in .env (checked local and parent)")

    client = genai.Client(api_key=api_key)
    return client


def ping():
    """Verify API connectivity with a minimal request (Readiness Probe)."""
    try:
        client = get_client()
        response = client.models.generate_content(
            model="gemma-3-27b-it", contents="Say 'OK'"
        )
        return response and response.text
    except Exception as e:
        raise ConnectionError(f"API Connectivity Check Failed: {e}")


def translate_text(text, model_id="gemma-3-27b-it"):
    """
    Core translation logic for Japanese-to-English technical prompts.
    Appends the mandatory '(Must respond in Japanese)' instruction.
    """
    client = get_client()
    prompt = f"Translate the following Japanese text to English. Output ONLY the English translation. After the translation, add ' (Must respond in Japanese)'.\n\nJapanese Text: {text}"

    response = client.models.generate_content(model=model_id, contents=prompt)
    if response and response.text:
        return response.text.strip()
    else:
        raise ValueError("Empty response from AI")


def main():
    """CLI entry point for Node.js bridge consumption."""
    if len(sys.argv) < 2:
        print("Usage: python translator.py <text>", file=sys.stderr)
        sys.exit(1)

    text = " ".join(sys.argv[1:])
    try:
        translated = translate_text(text)
        print(json.dumps({"translatedText": translated}))
    except Exception as e:
        # Emit errors as JSON for clean bridge parsing
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
