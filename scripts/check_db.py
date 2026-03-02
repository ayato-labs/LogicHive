"""Quick diagnostic: check which Supabase project the Hub .env connects to."""
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "LogicHive-Hub-Private", "backend", ".env"))

url = os.environ.get("SUPABASE_URL", "NOT SET")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "NOT SET")

print(f"URL: {url}")
print(f"KEY: {key[:30]}...")

from supabase import create_client

try:
    sb = create_client(url, key)
except Exception as e:
    print(f"CLIENT INIT FAILED: {e}")
    exit(1)

print("--- logichive_functions ---")
try:
    res = sb.table("logichive_functions").select("name").limit(3).execute()
    print(f"OK: {len(res.data)} rows")
    for r in res.data:
        print(f"  {r['name']}")
except Exception as e:
    print(f"FAIL: {e}")

print("--- organizations ---")
try:
    res = sb.table("organizations").select("name,plan_type").limit(3).execute()
    print(f"OK: {len(res.data)} rows")
    for r in res.data:
        print(f"  {r['name']} [{r['plan_type']}]")
except Exception as e:
    print(f"FAIL: {e}")

print("--- generated_reports ---")
try:
    res = sb.table("generated_reports").select("title").limit(1).execute()
    print(f"OK: {len(res.data)} rows")
except Exception as e:
    print(f"FAIL: {e}")

print("DONE")
