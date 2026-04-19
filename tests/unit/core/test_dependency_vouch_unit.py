import os
import tempfile
from pathlib import Path

import pytest

from core.evaluation.plugins.dependency_vouch import DependencyVouchEvaluator


@pytest.mark.asyncio
async def test_dependency_stdlib_allowed():
    """Unit: Standard library imports should be allowed (including expanded whitelist)."""
    evaluator = DependencyVouchEvaluator()
    # Test common ones plus the newly added ones (random, enum)
    code = "import os\nimport sys\nimport random\nimport enum\nfrom typing import List"
    result = await evaluator.evaluate(code, "python")
    assert result.score == 100.0


@pytest.mark.asyncio
async def test_dependency_hallucination_blocked():
    """Unit: Undeclared external libraries should be penalized."""
    evaluator = DependencyVouchEvaluator()
    code = "import non_existent_super_lib_abc"
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            result = await evaluator.evaluate(code, "python")
            assert result.score < 100.0
            assert "hallucinated" in result.reason.lower()
        finally:
            os.chdir(old_cwd)


@pytest.mark.asyncio
async def test_dependency_declared_allowed():
    """Unit: Libraries declared in requirements.txt should be allowed."""
    code = "import requests\nimport pandas"
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            with open("requirements.txt", "w") as f:
                f.write("requests==2.25.1\npandas>=1.2.0")

            # Re-instantiate to pick up new requirements.txt
            evaluator = DependencyVouchEvaluator()
            result = await evaluator.evaluate(code, "python")
            assert result.score == 100.0
        finally:
            os.chdir(old_cwd)


@pytest.mark.asyncio
async def test_dependency_local_module_allowed():
    """Unit: Local .py files should be allowed as imports."""
    code = "import my_local_tool"
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            # Create a dummy local module
            Path("my_local_tool.py").touch()

            evaluator = DependencyVouchEvaluator()
            result = await evaluator.evaluate(code, "python")
            assert result.score == 100.0
        finally:
            os.chdir(old_cwd)
