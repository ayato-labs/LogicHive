import os
from pathlib import Path

# ==========================================
# 🛡️ LogicHive: User Configuration Section
# ==========================================
# 機密情報や環境固有の設定を一箇所にまとめます。
# 必要に応じて環境変数での上書き（Override）も可能です。

# 1. AI & Models
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_TYPE = os.getenv("MODEL_TYPE", "gemini")  # "gemini" or "ollama"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemma-3-27b-it")
EMBEDDING_MODEL_ID = os.getenv("EMBEDDING_MODEL_ID", "gemini-embedding-001")

# 2. Ollama Fallback (Internal use or alternative)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral-large-3:675b-cloud")

# 3. Server Config
PORT = int(os.getenv("PORT", "10880"))
HOST = os.getenv("HOST", "0.0.0.0")

# 4. Search & Vector Config
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", 768))

# ==========================================
# ⚙️ Internal System Configuration
# ==========================================

# Base Paths
BASE_DIR = Path(__file__).parent.parent.resolve().absolute()
PROJECT_ROOT = BASE_DIR.parent.resolve()

# Handle Cloud Run or other container environments
IS_CLOUD = os.getenv("K_SERVICE") is not None or os.name != "nt"

if IS_CLOUD:
    # Use /tmp for ALL transient operations in the cloud
    DATA_DIR = Path("/tmp/logic-hive")
else:
    # Local dev fallback: Consolidate to storage/data at root
    DEFAULT_DATA_DIR = (BASE_DIR / "storage" / "data").resolve().absolute()
    DATA_DIR = Path(os.getenv("DATA_DIR", str(DEFAULT_DATA_DIR))).resolve().absolute()

# Ensure transient directory exists
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"[CRITICAL] Failed to create data directory {DATA_DIR}: {e}")

# SQLite Config
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", str(DATA_DIR / "logichive.db"))

# LogicHive Quality Gate & Storage Thresholds
QUALITY_GATE_THRESHOLD = int(os.getenv("QUALITY_GATE_THRESHOLD", 70))
DESCRIPTION_MIN_LENGTH = int(os.getenv("DESCRIPTION_MIN_LENGTH", 10))

# Vector Search (FAISS) Config
FAISS_GHOST_REBUILD_THRESHOLD = int(os.getenv("FAISS_GHOST_REBUILD_THRESHOLD", 10))
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", str(DATA_DIR / "faiss_index.bin"))
FAISS_MAPPING_PATH = os.getenv("FAISS_MAPPING_PATH", str(DATA_DIR / "faiss_mapping.json"))

# Legacy / Platform Compat
TRANSPORT = os.getenv("TRANSPORT", "http")
HUB_URL = os.getenv("HUB_URL", "https://function-store-hub-344411298688.asia-northeast1.run.app")
EXECUTION_MODE = os.getenv("EXECUTION_MODE", "auto")
