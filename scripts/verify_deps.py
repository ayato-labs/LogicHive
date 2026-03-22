import sys
import os

sys.path.append(os.path.abspath("src"))

from orchestrator import extract_python_dependencies

test_code = """
import numpy as np
from PIL import Image
import os
import sys
import json
from .relative import something
import requests
"""

deps = extract_python_dependencies(test_code)
print(f"Extracted Dependencies: {deps}")

expected = [
    "numpy",
    "requests",
]  # PIL -> pillow or something? No, it just extracts 'PIL'.
# Note: it extracts the base package name from the import statement.

if "numpy" in deps and "requests" in deps and "PIL" in deps:
    print("✅ AST Extraction Verified (External packages detected)")
if "os" not in deps and "sys" not in deps and "json" not in deps:
    print("✅ AST Extraction Verified (Std libs filtered)")
if "relative" not in deps:
    print("✅ AST Extraction Verified (Relative imports ignored)")
