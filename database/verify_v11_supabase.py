import httpx
import time

HUB_URL = "https://logichive-hub-344411298688.asia-northeast1.run.app"


def verify_supabase_integration():
    print("--- LogicHive v11 Verification (Supabase + 768d) ---")

    with httpx.Client(timeout=60.0) as client:
        # 1. Health Check
        print("\n[Step 1] Health Check...")
        try:
            resp = client.get(f"{HUB_URL}/health")
            data = resp.json()
            print(f"Status: {resp.status_code}, Version: {data.get('v')}")
            if resp.status_code != 200:
                print("Health check failed. Aborting.")
                return
        except Exception as e:
            print(f"Request failed: {e}")
            return

        # 1.5 Check Count (Debug List)
        print("\n[Step 1.5] Debug: Listing functions in Supabase...")
        try:
            list_resp = client.get(f"{HUB_URL}/api/v1/functions/debug/list")
            if list_resp.status_code == 200:
                functions = list_resp.json()
                print(f"Total functions in Supabase: {len(functions)}")
                for f in functions:
                    print(f" - {f['name']} (Created: {f['created_at']})")
            else:
                print(f"Debug list failed: {list_resp.status_code}")
        except Exception as e:
            print(f"Debug list request failed: {e}")

        # 2. Push Function
        print("\n[Step 2] Pushing a test function...")
        test_func = {
            "name": "calculate_shannon_entropy",
            "code": "import math\n\ndef calculate_shannon_entropy(probabilities):\n    return -sum(p * math.log2(p) for p in probabilities if p > 0)",
            "description": "Calculates the Shannon entropy for a given list of probabilities.",
            "tags": ["math", "information-theory", "entropy"],
        }

        try:
            push_resp = client.post(f"{HUB_URL}/api/v1/sync/push", json=test_func)
            print(f"Push Status: {push_resp.status_code}")
            if push_resp.status_code == 200:
                print("SUCCESS: Function pushed to Hub and synced to Supabase.")
            else:
                print(f"FAILED: {push_resp.text}")
                return
        except Exception as e:
            print(f"Push request failed: {e}")
            return

        # Wait a moment for any background processing (though it should be sync)
        time.sleep(2)

        # 3. Search Function
        print("\n[Step 3] Vector Search (Semantic)...")
        search_query = {
            "query": "How to calculate the entropy of a distribution?",
            "match_threshold": 0.1,
            "match_count": 3,
        }

        try:
            search_resp = client.post(
                f"{HUB_URL}/api/v1/functions/search", json=search_query
            )
            print(f"Search Status: {search_resp.status_code}")
            results = search_resp.json()
            print(f"Results: {results}")
            if search_resp.status_code == 200:
                print(f"Found {len(results)} results.")
                for r in results:
                    print(f" - {r['name']} (Similarity: {r.get('similarity', 'N/A')})")

                # Check if our function is in the results
                names = [r["name"] for r in results]
                if "calculate_shannon_entropy" in names:
                    print(
                        "\nVERIFICATION PASSED: Semantic search successfully retrieved the Supabase record."
                    )
                else:
                    print(
                        "\nVERIFICATION FAILED: Test function not found in search results."
                    )
            else:
                print(f"FAILED: {search_resp.text}")
        except Exception as e:
            print(f"Search request failed: {e}")


if __name__ == "__main__":
    verify_supabase_integration()
