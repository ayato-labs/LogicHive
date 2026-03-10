import os
import sys
# Add src to path
sys.path.append(os.path.abspath("src"))

from google import genai
from core.config import GEMINI_API_KEY

def test_models():
    client = genai.Client(api_key=GEMINI_API_KEY)
    test_ids = [
        "gemini-1.5-flash",
        "models/gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-2.0-flash-exp",
        "gemini-1.0-pro"
    ]
    
    for mid in test_ids:
        print(f"Testing model ID: '{mid}'...")
        try:
            response = client.models.generate_content(
                model=mid,
                contents=["hi"]
            )
            print(f"  SUCCESS! Response: {response.text[:20]}...")
            return mid
        except Exception as e:
            print(f"  FAILED: {e}")
    return None

if __name__ == "__main__":
    test_models()
