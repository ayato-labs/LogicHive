import functools
import time
from collections.abc import Callable


def resilient_retry(retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Advanced decorator providing exponential backoff for resilient function execution.
    Designed for production environments where network or transient failures are expected.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == retries - 1:
                        raise e
                    time.sleep(current_delay)
                    current_delay *= backoff

        return wrapper

    return decorator
