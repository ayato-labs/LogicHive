import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from core.evaluation.plugins.deterministic import DeterministicEvaluator

async def test_rejection_logic():
    evaluator = DeterministicEvaluator()
    
    # 1. Fake Assert Theater (Python)
    code = "def add(a, b): return a + b"
    fake_test = """
def test_add():
    assert True
    assert 1 == 1
    assert "a" == "a"
"""
    print("--- Testing 'Assert Theater' (Python) ---")
    res = await evaluator.evaluate(code, "python", test_code=fake_test)
    print(f"Score: {res.score}")
    print(f"Reason: {res.reason}")
    print(f"Valid Test (Calls code?): {res.details['is_valid_test']}")
    print()

    # 2. Honest Test (Python)
    honest_test = """
def test_add():
    from main import add
    assert add(1, 2) == 3
"""
    print("--- Testing 'Honest Test' (Python) ---")
    # Note: _verify_test_calls_code_python looks for 'add' in test_tree
    res = await evaluator.evaluate(code, "python", test_code=honest_test)
    print(f"Score: {res.score}")
    print(f"Reason: {res.reason}")
    print()

    # 3. Multi-language Support (JS)
    js_test = "expect(sum(1, 2)).toBe(3);"
    print("--- Testing 'JS Support' ---")
    res = await evaluator.evaluate("function sum(a, b) { return a+b; }", "javascript", test_code=js_test)
    print(f"Score: {res.score}")
    print(f"Reason: {res.reason}")
    print(f"Assertion Count: {res.details['assertion_count']}")

if __name__ == "__main__":
    asyncio.run(test_rejection_logic())
