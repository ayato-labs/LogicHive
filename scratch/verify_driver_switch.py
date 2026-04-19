import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

import core.config as config
from core.execution.factory import ExecutorFactory


def test_driver_switching():
    # 1. Test Local (default)
    config.EXECUTION_DRIVER = "local"
    executor = ExecutorFactory.get_executor("python")
    print(f"Driver [local]: {type(executor).__name__}")

    # 2. Test Docker
    config.EXECUTION_DRIVER = "docker"
    # We might need to reload or just call get_executor again
    executor = ExecutorFactory.get_executor("python")
    print(f"Driver [docker]: {type(executor).__name__}")


if __name__ == "__main__":
    test_driver_switching()
