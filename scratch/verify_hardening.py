import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure we can import from src
sys.path.append(os.path.join(os.getcwd(), "src"))

from core.evaluation.base import EvaluationResult
from core.evaluation.manager import EvaluationManager
from core.evaluation.plugins.ai import AIGateEvaluator
from core.evaluation.plugins.security_static import SecurityStaticEvaluator
from storage.sqlite_api import sqlite_storage

async def verify_hardening():
    print("=== LogicHive Hardening Verification ===\n")
    all_passed = True

    # 1. Verify Storage Fix (get_function_count)
    print("1. Testing SqliteStorage.get_function_count()...")
    try:
        count = await sqlite_storage.get_function_count()
        print(f"   [SUCCESS] Count retrieved: {count}")
    except AttributeError:
        print("   [FAILURE] get_function_count method not found!")
        all_passed = False
    except Exception as e:
        print(f"   [FAILURE] Error calling count: {e}")
        all_passed = False

    # 2. Verify AI Gate Resilience (System Error vs Logic Error)
    print("\n2. Testing AIGateEvaluator Resilience...")
    # Mock LogicIntelligence to simulate an API failure
    mock_intel = MagicMock()
    mock_intel.evaluate_quality = MagicMock(side_effect=Exception("Simulated API Down"))
    
    ai_gate = AIGateEvaluator(api_key="fake", intel=mock_intel)
    try:
        res = await ai_gate.evaluate("def test(): pass", "python")
        if res.is_system_error and "Transient Error" in res.reason:
            print("   [SUCCESS] AI Gate correctly identified transient failure as SYSTEM_ERROR.")
        else:
            print(f"   [FAILURE] Unexpected result: score={res.score}, is_system_error={res.is_system_error}")
            all_passed = False
    except Exception as e:
        print(f"   [FAILURE] AI Gate crashed instead of returning result: {e}")
        all_passed = False

    # 3. Verify Security Static Differentiation (Syntax Error = Logic Error)
    print("\n3. Testing SecurityStatic Differentiator...")
    sec_gate = SecurityStaticEvaluator()
    bad_syntax = "def broken(:" # Missing closing paren
    try:
        res = await sec_gate.evaluate(bad_syntax, "python")
        if not res.is_system_error and "Logic Error (Syntax Error)" in res.reason:
            print("   [SUCCESS] Security Gate correctly identified SyntaxError as LOGIC_ERROR (no is_system_error).")
        else:
            print(f"   [FAILURE] Unexpected result: score={res.score}, is_system_error={res.is_system_error}")
            all_passed = False
    except Exception as e:
        print(f"   [FAILURE] Security Gate crashed: {e}")
        all_passed = False

    # 4. Verify Evaluation Manager Aggregation
    print("\n4. Testing EvaluationManager Aggregation...")
    manager = EvaluationManager()
    # Mock one of the evaluators to return a system error
    # We find an evaluator that isn't structural
    evaluator_to_mock = next((e for e in manager.evaluators if e.name == "ai_gate"), None)
    if evaluator_to_mock:
        with patch.object(evaluator_to_mock, 'evaluate', return_value=EvaluationResult(score=0.0, reason="System Failure", is_system_error=True)):
            # We must provide some code that passes structural check
            good_code = "def foo():\n  return 1"
            good_test = "def test_foo():\n  assert foo() == 1"
            
            agg_res = await manager.evaluate_all(good_code, "python", test_code=good_test)
            if agg_res.get("is_system_error") == True:
                print("   [SUCCESS] Manager correctly aggregated is_system_error flag.")
            else:
                print(f"   [FAILURE] Manager failed to aggregate error flag: {agg_res}")
                all_passed = False
    else:
        print("   [SKIP] ai_gate not loaded for mocking.")

    print("\n" + "="*40)
    if all_passed:
        print("FINAL VERIFICATION: PASSED")
    else:
        print("FINAL VERIFICATION: FAILED")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(verify_hardening())
