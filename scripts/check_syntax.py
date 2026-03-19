import sys

def check_file(path):
    print(f"Checking {path}...")
    try:
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        compile(code, path, "exec")
        print("✅ No syntax errors.")
    except SyntaxError as e:
        print(f"❌ Syntax Error in {path}:")
        print(f"  Line {e.lineno}: {e.text}")
        print(f"  Error: {e.msg}")
    except Exception as e:
        print(f"❌ Error in {path}: {e}")

if __name__ == "__main__":
    check_file("src/storage/sqlite_api.py")
    check_file("src/storage/auto_backup.py")
    check_file("src/orchestrator.py")
