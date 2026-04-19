import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from core.evaluation.plugins.static import RuffEvaluator


async def test_ruff_fidelity():
    evaluator = RuffEvaluator()

    # Code with obvious ruff issues (unused import, line too long, etc.)
    code = """
import os
import sys

def my_function():
    x = 10
    print("Hello")
"""
    print("--- Testing Ruff High-Fidelity Feedback ---")
    res = await evaluator.evaluate(code, "python")
    print(f"Score: {res.score}")
    print(f"Detailed Reason: {res.reason}")


if __name__ == "__main__":
    asyncio.run(test_ruff_fidelity())
