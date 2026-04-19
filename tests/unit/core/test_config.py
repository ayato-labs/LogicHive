import pytest
from core.config import DEFAULT_VERIFICATION_TIMEOUT, MAX_VERIFICATION_TIMEOUT

def test_timeout_config_values():
    """Unit: Verify that timeout constants are set to expected safety values."""
    # Based on the requirement: default=60, hard limit=120
    assert DEFAULT_VERIFICATION_TIMEOUT == 60
    assert MAX_VERIFICATION_TIMEOUT == 120
    assert DEFAULT_VERIFICATION_TIMEOUT < MAX_VERIFICATION_TIMEOUT
