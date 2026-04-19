import os
import sys

# Add src to path
sys.path.append(os.path.abspath("src"))

from google import genai

from core.config import GEMINI_API_KEY


def find_first_working():
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("Listing models...")
    try:
        models = list(client.models.list())
        print(f"Total models available: {len(models)}")

        for m in models:
            mid = m.name  # e.g. 'models/gemini-1.5-flash'
            print(f"Attempting to use: {mid}...")
            try:
                # Try with a very simple request
                resp = client.models.generate_content(model=mid, contents="hi")
                print(f"  !! SUCCESS with {mid}: {resp.text[:20]}...")
                return mid
            except Exception as e:
                print(f"  FAILED with {mid}: {e}")

    except Exception as e:
        print(f"CRITICAL ERROR listing models: {e}")
    return None


if __name__ == "__main__":
    find_first_working()
