import subprocess
import time

code = """
import hashlib
def calculate_code_hash(code: str) -> str:
    normalized_code = code.strip().replace("\\r\\n", "\\n")
    return hashlib.sha256(normalized_code.encode("utf-8")).hexdigest()

code_val = "def hello():\\n    print('world')"
print(calculate_code_hash(code_val))
"""

with open("debug_hash.py", "w") as f:
    f.write(code)

start = time.perf_counter()
res = subprocess.run(
    ["uv", "run", "--quiet", "--offline", "--no-project", "python", "debug_hash.py"],
    capture_output=True,
    text=True,
)
end = time.perf_counter()

print(f"Status: {res.returncode}")
print(f"Stdout: {res.stdout}")
print(f"Stderr: {res.stderr}")
print(f"Duration: {end - start:.2f}s")
