import os
import sys

# Add src to path
sys.path.append(os.path.abspath("src"))

from google import genai
from core.config import GEMINI_API_KEY


def list_models():
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("Available models:")
    try:
        # In the new SDK, it's client.models.list()
        # Returns an iterator over Model objects
        for m in client.models.list():
            # In the new SDK, m.name usually contains the ID string
            print(f"Name: {m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")


if __name__ == "__main__":
    list_models()
