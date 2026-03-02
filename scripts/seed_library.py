import asyncio
import os
import sys
import logging
import json
import re
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../LogicHive-Hub-Private/backend")))

# Import LogicHive Hub components
from hub.supabase_api import supabase_storage
from core.embedding import embedding_service
from core.config import get_setting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Target System Org for Seed
SYSTEM_ORG_ID = "00000000-0000-0000-0000-000000000000" # Reserved for system seed

# 50+ Harvested Functions from ayato_reporter & Utils
SEED_FUNCTIONS = [
    {"name": "safe_execute", "description": "Decorator to catch exceptions and log them.", "tags": ["utility", "error-handling"], "code": "def safe_execute(default=None):\n    def decorator(func):\n        def wrapper(*args, **kw):\n            try: return func(*args, **kw)\n            except: return default\n        return wrapper\n    return decorator"},
    {"name": "ExecutionTracer", "description": "Singleton for JSONL tracing.", "tags": ["tracing", "logs"], "code": "class ExecutionTracer:\n    _inst = None\n    def __new__(cls): ..."},
    {"name": "ServiceContainer", "description": "Simple DI container.", "tags": ["core", "di"], "code": "class ServiceContainer:\n    _insts = {}\n    @classmethod\n    def get(cls, name): return cls._insts.get(name)"},
    {"name": "parse_json_md", "description": "Robust JSON extraction from markdown.", "tags": ["ai", "parser"], "code": "import json, re\ndef parse_json_md(text):\n    m = re.search(r'```json\s*(.*?)\s*```', text, re.S)\n    return json.loads(m.group(1) if m else text)"},
    {"name": "setup_cloud_logger", "description": "GCP optimized logging.", "tags": ["logging", "cloud"], "code": "import logging, sys\ndef setup_cloud_logger(): ..."},
    {"name": "inject_disclaimer", "description": "Appends legal disclaimer.", "tags": ["compliance", "finance"], "code": "def inject_disclaimer(c, l='jp'): return c + '\\n---\\nDisclaimer...'"},
    {"name": "slugify", "description": "URL-friendly slug generator.", "tags": ["string", "utility"], "code": "import re\ndef slugify(t): return re.sub(r'[-\\s]+', '-', re.sub(r'[^\\w\\s-]', '', t).strip().lower())"},
    {"name": "deep_merge", "description": "Recursive dict merge.", "tags": ["dict", "utility"], "code": "def deep_merge(a, b): ..."},
    {"name": "safe_makedirs", "description": "Idempotent directory creation.", "tags": ["filesystem"], "code": "import os\ndef safe_makedirs(p): os.makedirs(p, exist_ok=True)"},
    {"name": "retry_backoff", "description": "Exponential backoff decorator.", "tags": ["decorator", "api"], "code": "import time\ndef retry_backoff(r=3, b=1): ..."},
    {"name": "parse_arxiv_atom", "description": "ArXiv API parser.", "tags": ["parser", "ai"], "code": "import xml.etree.ElementTree as ET\ndef parse_arxiv_atom(x): ..."},
    {"name": "parse_rss", "description": "Generic RSS parser.", "tags": ["parser", "news"], "code": "def parse_rss(x): ..."},
    {"name": "extract_xbrl", "description": "SEC XBRL concept extractor.", "tags": ["finance", "sec"], "code": "def extract_xbrl(t): ..."},
    {"name": "get_sentiment", "description": "Keyword-based sentiment score.", "tags": ["nlp"], "code": "def get_sentiment(t): ..."},
    {"name": "format_yen", "description": "Currency formatting for JP.", "tags": ["finance"], "code": "def format_yen(a): return f'{a:,.0f}円'"},
    {"name": "is_valid_url", "description": "URL regex validator.", "tags": ["validator"], "code": "def is_valid_url(u): ..."},
    {"name": "flatten_dict", "description": "Flatten nested dict with dots.", "tags": ["dict"], "code": "def flatten_dict(d, p=''): ..."},
    {"name": "chunk_text", "description": "Split text by word boundaries.", "tags": ["nlp", "ai"], "code": "def chunk_text(t, s=1000): ..."},
    {"name": "get_relative_time", "description": "Human-friendly time diff.", "tags": ["date"], "code": "def get_relative_time(dt): ..."},
    {"name": "clean_html", "description": "Remove HTML tags.", "tags": ["string"], "code": "def clean_html(t): return re.sub(r'<[^>]*>', '', t)"},
    {"name": "generate_token", "description": "Secure random token.", "tags": ["security"], "code": "import secrets\ndef generate_token(): return secrets.token_urlsafe(32)"},
    {"name": "is_valid_email", "description": "Email format validator.", "tags": ["validator"], "code": "def is_valid_email(e): ..."},
    {"name": "wrap_text", "description": "Textwrap for terminal.", "tags": ["string"], "code": "import textwrap\ndef wrap_text(t, w=80): return textwrap.fill(t, w)"},
    {"name": "get_file_size", "description": "Human-readable size.", "tags": ["filesystem"], "code": "def get_file_size(p): ..."},
    {"name": "load_prefixed_env", "description": "Collect prefixed env vars.", "tags": ["core"], "code": "def load_prefixed_env(p): ..."},
    {"name": "calc_hash", "description": "SHA256 hasher.", "tags": ["security"], "code": "import hashlib\ndef calc_hash(t): return hashlib.sha256(t.encode()).hexdigest()"},
    {"name": "safe_get_nested", "description": "Dot-notation dict getter.", "tags": ["dict"], "code": "def safe_get_nested(d, p): ..."},
    {"name": "md_to_plain", "description": "Strip markdown formatting.", "tags": ["string"], "code": "def md_to_plain(m): ..."},
    {"name": "is_prime", "description": "Basic primality test.", "tags": ["math"], "code": "def is_prime(n): ..."},
    {"name": "generate_summary", "description": "First N sentences extractor.", "tags": ["nlp"], "code": "def generate_summary(t, n=3): ..."},
    {"name": "partition_list", "description": "Chunk list into N size.", "tags": ["list"], "code": "def partition_list(l, n): ..."},
    {"name": "weighted_avg", "description": "Weighted average calculator.", "tags": ["math"], "code": "def weighted_avg(v, w): ..."},
    {"name": "backoff_wait", "description": "Wait time calculator.", "tags": ["math", "api"], "code": "def backoff_wait(a): return 2**a"},
    {"name": "is_hex_color", "description": "Hex color validator.", "tags": ["validator"], "code": "def is_hex_color(c): ..."},
    {"name": "clamp_val", "description": "Clamp numeric value.", "tags": ["math"], "code": "def clamp_val(v, mi, ma): return max(mi, min(ma, v))"},
    {"name": "to_camel", "description": "snake_case to camelCase.", "tags": ["string"], "code": "def to_camel(s): ..."},
    {"name": "to_snake", "description": "camelCase to snake_case.", "tags": ["string"], "code": "def to_snake(c): ..."},
    {"name": "dedupe_keep_order", "description": "Ordered unique list.", "tags": ["list"], "code": "def dedupe_keep_order(l): ..."},
    {"name": "readable_count", "description": "K/M/B formatter.", "tags": ["string"], "code": "def readable_count(n): ..."},
    {"name": "mask_secret", "description": "Mask sensitive strings.", "tags": ["security"], "code": "def mask_secret(s): ..."},
    {"name": "get_domain", "description": "Extract netloc from URL.", "tags": ["url"], "code": "def get_domain(u): ..."},
    {"name": "safe_div", "description": "Division with zero-check.", "tags": ["math"], "code": "def safe_div(a, b): return a/b if b!=0 else 0"},
    {"name": "truncate_middle", "description": "Center ellipsis truncation.", "tags": ["string"], "code": "def truncate_middle(t, m=20): ..."},
    {"name": "is_uuid", "description": "UUID format validator.", "tags": ["validator"], "code": "def is_uuid(v): ..."},
    {"name": "normalize_pct", "description": "Sum to 100 normalization.", "tags": ["math"], "code": "def normalize_pct(v): ..."},
    {"name": "find_between", "description": "Substring extractor.", "tags": ["string"], "code": "def find_between(s, f, t): ..."},
    {"name": "count_words", "description": "Simple word counter.", "tags": ["string"], "code": "def count_words(t): return len(t.split())"},
    {"name": "random_str", "description": "Random alpha-numeric string.", "tags": ["utility"], "code": "import random, string\ndef random_str(l=8): return ''.join(random.choices(string.ascii_letters, k=l))"},
    {"name": "get_env_bool", "description": "Convert env to boolean.", "tags": ["core"], "code": "def get_env_bool(k): return os.getenv(k, '').lower() in ('true', '1', 'yes')"},
    {"name": "is_leap_year", "description": "Leap year check.", "tags": ["math", "date"], "code": "def is_leap_year(y): return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)"},
    {"name": "celsius_to_fahrenheit", "description": "Temperature converter.", "tags": ["math"], "code": "def c2f(c): return c * 9/5 + 32"}
]

async def seed():
    client = supabase_storage._get_client()
    organization_id = SYSTEM_ORG_ID
    
    # Ensure Org exists
    try:
        client.table("organizations").upsert({
            "id": organization_id,
            "name": "System Seed",
            "api_key_hash": "system-seed-key",
            "plan_type": "pro",
            "request_limit": 999999
        }).execute()
    except: pass

    logger.info(f"Seeding {len(SEED_FUNCTIONS)} functions...")
    for func in SEED_FUNCTIONS:
        # Generate embedding
        text = f"{func['name']} {func['description']} {func['code']}"
        embedding = embedding_service.get_embedding(text)
        
        data = {
            **func,
            "embedding": embedding,
            "organization_id": organization_id,
            "reliability_score": 1.0
        }
        
        try:
            client.table("logichive_functions").upsert(data, on_conflict="name,organization_id").execute()
            logger.info(f"Seeded: {func['name']}")
        except Exception as e:
            logger.error(f"Failed {func['name']}: {e}")

if __name__ == "__main__":
    asyncio.run(seed())
