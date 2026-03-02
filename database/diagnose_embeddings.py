import httpx

HUB_URL = "https://logichive-hub-344411298688.asia-northeast1.run.app"


def diagnose_embeddings():
    print("--- Embedding Similarity Diagnosis ---")

    with httpx.Client(timeout=30.0) as client:
        # 1. Get query embedding
        query = "How to calculate the entropy of a distribution?"
        print(f"Query: {query}")

        # We'll use the search endpoint but with threshold -1.0 if possible
        # Or just trust the Hub's embedding generation for now.

        # 2. Get the stored function from debug list
        list_resp = client.get(f"{HUB_URL}/api/v1/functions/debug/list")
        if list_resp.status_code != 200:
            print("Failed to list")
            return

        # Actually we need the actual embedding from the DB.
        # Let's add an endpoint to get the FULL record including embedding!
        print("Need full record including embedding for comparison.")


if __name__ == "__main__":
    diagnose_embeddings()
