import pytest

from core.evaluation.plugins.deterministic import DeterministicEvaluator


@pytest.mark.asyncio
async def test_count_assertions():
    evaluator = DeterministicEvaluator()

    # Direct assert
    assert evaluator._count_assertions("assert 1 == 1") == 1

    # Multiple asserts
    assert evaluator._count_assertions("assert 1\nassert 2") == 2

    # Pytest / Unittest style calls
    test_code = """
import pytest
def test_func():
    pytest.assume(True)
    self.assertEqual(1, 1)
    unittest.TestCase().assertTrue(True)
    assert_called_with(x=1)
"""
    # self.assertEqual -> assert prefix (1)
    # assertTrue -> assert prefix (1)
    # assert_called_with -> assert prefix (1)
    # Total = 3
    assert evaluator._count_assertions(test_code) == 3

@pytest.mark.asyncio
async def test_find_hollow_methods():
    evaluator = DeterministicEvaluator()

    # 1. 'pass'
    code_pass = "def hollow():\n    pass"
    assert "hollow" in evaluator._find_hollow_methods(code_pass)

    # 2. '...'
    code_ellipsis = "def hollow_dots():\n    ..."
    assert "hollow_dots" in evaluator._find_hollow_methods(code_ellipsis)

    # 3. Identity return
    code_identity = "def identity(x):\n    return x"
    assert "identity" in evaluator._find_hollow_methods(code_identity)

    # 4. Identity return with other args
    code_id_multi = "def first(a, b):\n    return a"
    assert "first" in evaluator._find_hollow_methods(code_id_multi)

    # 5. Non-hollow (logic before return)
    code_logic = "def logic(x):\n    y = x + 1\n    return y"
    assert "logic" not in evaluator._find_hollow_methods(code_logic)

@pytest.mark.asyncio
async def test_deterministic_evaluate_python_scores():
    evaluator = DeterministicEvaluator()

    # Zero assertion case
    res_zero = await evaluator.evaluate("def f(): return 1", "python", test_code="f()")
    assert res_zero.score == 0.0
    assert "CRITICAL" in res_zero.reason

    # Low density case (1 assertion)
    res_low = await evaluator.evaluate("def f(): return 1", "python", test_code="assert f() == 1")
    # 100 - (3-1)*20 = 60
    assert res_low.score == 60.0

    # Hollow logic penalty
    code_hollow = "def hollow(): pass"
    test_hollow = "assert True\nassert True\nassert True" # 3 assertions (100)
    res_hollow = await evaluator.evaluate(code_hollow, "python", test_code=test_hollow)
    # 100 - 30 = 70
    assert res_hollow.score == 70.0

@pytest.mark.asyncio
async def test_deterministic_skip_non_python():
    evaluator = DeterministicEvaluator()
    res = await evaluator.evaluate("function f() {}", "javascript")
    assert res.score == 100.0
    assert "Skipped" in res.reason
