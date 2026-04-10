import os
import sys

# Add src to path
sys.path.append(os.path.abspath("src"))

from google import genai
from core.config import GEMINI_API_KEY


def list_models():
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("Exact model IDs:")
    try:
        for m in client.models.list():
            # Stripping 'models/' prefix if the SDK expects just the name
            # OR keeping it if it wants it. Let's see what it returns.
            print(f"'{m.name}'")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    list_models()
