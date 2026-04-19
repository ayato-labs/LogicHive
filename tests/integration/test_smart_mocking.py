import pytest

from core.evaluation.plugins.deterministic import DeterministicEvaluator
from orchestrator import do_save_async


@pytest.mark.asyncio
async def test_heavy_import_detection():
    evaluator = DeterministicEvaluator()
    code = """
import torch
import numpy as np

def foo():
    return torch.abs(-1)
"""
    res = await evaluator.evaluate(code, "python", test_code="assert True")
    assert "heavy_imports" in res.details
    assert "torch" in res.details["heavy_imports"]
    assert "Performance Warning: Module-level heavy imports detected" in res.reason


@pytest.mark.asyncio
async def test_smart_mocking_success(test_db):
    # This code would fail without mocking or lazy import because 'torch' is not necessarily installed or is heavy
    code = """
import torch

def get_torch_version():
    return torch.__version__
"""
    test_code = """
import torch
v = get_torch_version()
assert isinstance(v, (str, object)) # MagicMock will return a mock object
"""

    # We use mock_imports to bypass real torch load
    success = await do_save_async(
        name="test_mock_logic",
        code=code,
        test_code=test_code,
        description="Testing smart mocking",
        mock_imports=["torch"],
        project="test_system",
    )

    assert success is True
