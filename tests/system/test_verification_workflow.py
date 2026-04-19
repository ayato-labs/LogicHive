import pytest

from orchestrator import do_get_async, do_save_async


@pytest.mark.asyncio
async def test_system_save_and_verify_success(test_db):
    """
    Full workflow test: Save code with valid test.
    Checks that the asset is stored in the database.
    """
    name = "system_valid_func"
    code = "def greet(name): return f'Hello, {name}!'"
    test_code = "assert greet('World') == 'Hello, World!'"

    result = await do_save_async(
        name=name,
        code=code,
        test_code=test_code,
        description="System verification test",
        tags=["system-test"],
    )

    # Check result (do_save_async returns True on success)
    assert result is True

    # Check DB via orchestrated call
    stored = await do_get_async(name)
    assert stored is not None
    assert stored["code"] == code


@pytest.mark.asyncio
async def test_system_save_and_verify_failure(test_db):
    """
    Full workflow test: Save code with failing test.
    Checks that the save is REJECTED (raises ValidationError).
    """
    from core.exceptions import ValidationError

    name = "system_faulty_func"
    code = "def greet(name): return 'Goodbye'"
    test_code = "assert greet('World') == 'Hello, World!'"

    with pytest.raises(ValidationError) as exc_info:
        await do_save_async(
            name=name, code=code, description="This should fail", test_code=test_code
        )

    assert "Quality Gate rejected" in str(exc_info.value)

    # Check DB (Should NOT exist)
    stored = await do_get_async(name)
    assert stored is None


@pytest.mark.asyncio
async def test_system_dependency_verification(test_db):
    """
    Workflow test: Code requiring external library.
    Checks that 'uv' handles dependencies during verification.
    """
    name = "dep_func"
    code = "import dateutil.parser\ndef parse(s): return dateutil.parser.parse(s).year"
    test_code = "assert parse('2026-01-01') == 2026"

    result = await do_save_async(
        name=name,
        code=code,
        description="Testing uv run with dependencies",
        test_code=test_code,
        dependencies=["python-dateutil"],
    )

    assert result is True
