import pytest

from core.evaluation.manager import EvaluationManager


@pytest.mark.asyncio
async def test_chaos_infinite_loop_resilience():
    """
    Chaos: Verify that an infinite loop in user code is killed within timeout.
    """
    manager = EvaluationManager()
    code = "def loop():\n    while True: pass"
    test_code = "loop()"

    # 2-second timeout to make it fast
    results = await manager.evaluate_all(
        code=code, language="python", test_code=test_code, timeout=2
    )

    runtime_res = results["details"]["runtime"]
    assert runtime_res["score"] == 0.0
    assert (
        "timeout" in runtime_res["reason"].lower()
        or "Possible infinite loop" in runtime_res["reason"]
    )


@pytest.mark.asyncio
async def test_chaos_network_access_blocked():
    """
    Chaos: Verify that network access attempts are blocked by the sandbox.
    """
    manager = EvaluationManager()
    code = "import socket\ndef dial():\n    s = socket.socket()\n    s.connect(('8.8.8.8', 53))"
    test_code = "try:\n    dial()\nexcept Exception as e:\n    print(f'CAUGHT: {e}')\n    raise e"

    results = await manager.evaluate_all(code=code, language="python", test_code=test_code)

    runtime_res = results["details"]["runtime"]
    assert runtime_res["score"] == 0.0
    assert "NETWORK_ACCESS_DENIED" in runtime_res["reason"]


@pytest.mark.asyncio
async def test_chaos_memory_bomb_resilience():
    """
    Chaos: Verify that a memory bomb is killed by the resource monitor.
    """
    manager = EvaluationManager()
    # Use bytearray for immediate allocation and sleep to ensure it's caught
    # 800MB is over 128MB limit
    code = "def bomb():\n    import time\n    data = bytearray(800 * 1024 * 1024)\n    data[0] = 1 # Force touch\n    time.sleep(2) # Sustain for monitor\n    return len(data)"
    test_code = "bomb()"

    # Set a strict memory limit for this test
    results = await manager.evaluate_all(
        code=code, language="python", test_code=test_code, memory_limit_mb=128
    )

    runtime_res = results["details"]["runtime"]
    assert runtime_res["score"] == 0.0
    assert "Memory limit exceeded" in runtime_res["reason"]


@pytest.mark.asyncio
async def test_chaos_infra_exception_isolation():
    """
    Chaos: Verify that even if an evaluator crashes with an unhandled Python exception,
    the manager isolates the error and returns a proper result object.
    """
    from core.evaluation.base import BaseEvaluator

    class CrashingEvaluator(BaseEvaluator):
        @property
        def name(self):
            return "crash_test"

        async def evaluate(self, code, lang, **kwargs):
            raise RuntimeError("CRASH SIMULATION")

    manager = EvaluationManager()
    # Inject the crashing evaluator
    manager.evaluators.append(CrashingEvaluator())

    results = await manager.evaluate_all(code="def ok(): pass", language="python", test_code="ok()")

    # The whole evaluation shouldn't crash, and we should have an error result for this evaluator
    assert "crash_test" in results["details"]
    assert results["details"]["crash_test"]["score"] == 0.0
    assert "CRASH SIMULATION" in results["details"]["crash_test"]["reason"]
