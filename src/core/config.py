import os
from pathlib import Path
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


# Base Paths
# Updated for statelessness: 2026-02-25
BASE_DIR = Path(__file__).parent.parent

# LogicHive Hub is PURE STATELESS.
# We use Environment Variables for everything. NO local settings.json.

# Handle Cloud Run or other container environments
IS_CLOUD = os.getenv("K_SERVICE") is not None or os.name != "nt"

if IS_CLOUD:
    # Use /tmp for ALL transient operations in the cloud
    DATA_DIR = Path("/tmp/logic-hive")
else:
    # Local dev fallback: Consolidate to storage/data at root
    DATA_DIR = Path(os.getenv("FS_DATA_DIR", BASE_DIR.parent / "storage" / "data"))


def get_setting(key: str, default=None):
    """Gets a setting from env var ONLY (Stateless priority)."""
    return os.getenv(key, default)


# Ensure transient directory exists
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    # Use a print here as logging might not be fully configured yet
    print(f"[CRITICAL] Failed to create data directory {DATA_DIR}: {e}")

# Server Config
HOST = get_setting("FS_HOST", "0.0.0.0")
# Cloud Run compatibility: standard PORT env var priority
PORT = int(os.getenv("PORT", get_setting("FS_PORT", "10880")))
TRANSPORT = get_setting("FS_TRANSPORT", "http")
HUB_URL = get_setting(
    "FS_HUB_URL", "https://function-store-hub-344411298688.asia-northeast1.run.app"
)

# AI Strategy Config
MODEL_TYPE = get_setting("FS_MODEL_TYPE", "gemini")  # "gemini" or "ollama"
GEMINI_API_KEY = get_setting("FS_GEMINI_API_KEY", "")
GEMINI_MODEL = get_setting("FS_GEMINI_MODEL", "models/gemma-3-27b-it")
OLLAMA_URL = get_setting("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = get_setting("OLLAMA_MODEL", "llama3")
EMBEDDING_MODEL_ID = get_setting("EMBEDDING_MODEL_ID", "gemini-embedding-001")

# Execution Runtime Config
# Options: "auto" (local venv), "docker" (containerized), "cloud" (managed)
EXECUTION_MODE = get_setting("FS_EXECUTION_MODE", "auto")

# SQLite Config
SQLITE_DB_PATH = get_setting("SQLITE_DB_PATH", str(DATA_DIR / "logichive.db"))

# LogicHive Quality Gate & Storage Thresholds
QUALITY_GATE_THRESHOLD = int(get_setting("QUALITY_GATE_THRESHOLD", 70))
DESCRIPTION_MIN_LENGTH = int(get_setting("DESCRIPTION_MIN_LENGTH", 10))

# Vector Search (FAISS) Config
VECTOR_DIMENSION = int(get_setting("VECTOR_DIMENSION", 768))
FAISS_GHOST_REBUILD_THRESHOLD = int(get_setting("FAISS_GHOST_REBUILD_THRESHOLD", 10))
FAISS_INDEX_PATH = get_setting("FAISS_INDEX_PATH", str(DATA_DIR / "faiss_index.bin"))
FAISS_MAPPING_PATH = get_setting("FAISS_MAPPING_PATH", str(DATA_DIR / "faiss_mapping.json"))
