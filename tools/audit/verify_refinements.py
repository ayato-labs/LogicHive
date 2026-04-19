import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.abspath("src"))

from core.exceptions import ValidationError
from orchestrator import do_save_async
from storage.sqlite_api import vector_manager


async def test_python_quality():
    print("--- Testing Python Quality Gate ---")
    bad_python = "def fail():\n  pass"  # Too trivial
    try:
        await do_save_async("fail_func", bad_python, "Trivial function", language="python")
        print("❌ Error: Trivial Python function should have been rejected.")
    except ValidationError:
        print("✅ Correctly rejected trivial Python.")

    good_python = """
def calculate_fibonacci(n: int) -> int:
    \"\"\"Calculates the nth Fibonacci number efficiently.\"\"\"
    if n <= 0: return 0
    if n == 1: return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""
    try:
        success = await do_save_async("fib_func", good_python, "Calculates fib", language="python")
        if success:
            print("✅ Successfully saved high-quality Python function.")
        else:
            print("❌ Error: Failed to save high-quality Python function.")
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_llm_syntax_gate():
    print("\n--- Testing LLM Syntax Gate (C++) ---")
    bad_cpp = "int main() { return 0 // Missing bracket"
    try:
        await do_save_async("bad_cpp", bad_cpp, "Missing bracket C++", language="cpp")
        print("❌ Error: Syntax-broken C++ should have been rejected by LLM.")
    except ValidationError:
        print("✅ Correctly rejected broken C++.")


async def test_faiss_rebuild():
    print("\n--- Testing FAISS Rebuild ---")
    # Initial count
    await vector_manager.rebuild_index()
    initial_total = vector_manager.index.ntotal
    print(f"Initial FAISS total: {initial_total}")

    # Rebuild
    await vector_manager.rebuild_index()
    after_rebuild = vector_manager.index.ntotal
    print(f"After rebuild total: {after_rebuild}")

    if initial_total == after_rebuild:
        print("✅ FAISS rebuild successful (consistent with DB).")
    else:
        print("❌ FAISS rebuild discrepancy detected.")


if __name__ == "__main__":
    asyncio.run(test_python_quality())
    asyncio.run(test_llm_syntax_gate())
    asyncio.run(test_faiss_rebuild())
