import sys
from unittest.mock import MagicMock


def apply_mocks(mock_list):
    for mod_name in mock_list:
        m = MagicMock()
        # Explicitly set some common attributes to be safe
        m.__version__ = "mock-1.0.0"
        sys.modules[mod_name] = m


code = """
import torch
def get_torch_version():
    return torch.__version__
"""

test_code = """
import torch
print(f"torch type: {type(torch)}")
try:
    v = get_torch_version()
    print(f"v: {v}")
except AttributeError as e:
    print(f"REPRODUCED: {e}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
"""

apply_mocks(["torch"])
globals_dict = {"__builtins__": __builtins__}
try:
    exec(code, globals_dict)
    exec(test_code, globals_dict)
except Exception as e:
    print(f"TOP LEVEL ERROR: {type(e).__name__}: {e}")
