import subprocess
import os
import httpx
import time
from pathlib import Path
from src.core.config import OLLAMA_URL

def check_ollama_running():
    """Check if Ollama server is responsive and healthy."""
    try:
        # Check /api/tags specifically as it's a standard Ollama endpoint
        resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=1.0)
        is_running = resp.status_code == 200
        if is_running:
            # Try to get version for extra verification
            try:
                version_resp = httpx.get(f"{OLLAMA_URL}/api/version", timeout=0.5)
                version = version_resp.json().get('version', 'unknown')
                print(f"[OLLAMA] Connected to Ollama version: {version}")
            except Exception:
                pass
        return is_running
    except Exception as e:
        # Log connection errors for debugging
        # print(f"[DEBUG] Ollama check failed: {e}")
        return False

def start_ollama():
    """Start Ollama server in background."""
    print(f"[OLLAMA] Ollama is not running (checked {OLLAMA_URL}). Starting Ollama server...")
    try:
        # Start in background without blocking
        proc = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        print(f"[OLLAMA] Process started with PID: {proc.pid}")
        # Give it a few seconds to initialize
        print("[OLLAMA] Waiting for Ollama (3s)...")
        time.sleep(3)
        if check_ollama_running():
            print("[OLLAMA] Server successfully started and responding.")
        else:
            print("[OLLAMA] Server process started but not responding yet. It might still be initializing.")
    except Exception as e:
        print(f"[ERROR] Failed to start Ollama: {e}")

def main():
    """Launcher for LogicHive Hub."""
    root = Path(__file__).parent.absolute()
    os.chdir(root)
    
    print("\n" + "="*60)
    print("LogicHive System Launcher")
    print("="*60)
    print(f"Project Root: {root}")

    # Step 1: Check & Start Ollama
    if not check_ollama_running():
        start_ollama()
    else:
        print("[OLLAMA] Ollama server is already running.")

    # Step 2: Launch UI
    ui_cmd = ["uv", "run", "streamlit", "run", "src/ui.py", "--server.headless", "true"]
    
    try:
        print("[PROCESS] Starting UI (Streamlit)...")
        subprocess.run(ui_cmd)
        
    except KeyboardInterrupt:
        print("\n[INFO] LogicHive System stopped by user.")
    except Exception as e:
        print(f"\n[ERROR] Failed to start LogicHive: {e}")

if __name__ == "__main__":
    main()
