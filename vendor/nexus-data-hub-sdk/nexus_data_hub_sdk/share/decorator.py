from functools import wraps
from typing import Callable, Any, Type
import time
import logging

logger = logging.getLogger(__name__)


def exception_wrapper(exception: Type[Exception]):
    def decorator(f: Callable[[Any], Any]):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                raise exception(str(e)) from e
        return wrapper
    return decorator


def retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    A decorator that retries a function call with exponential backoff.

    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
    """
    def decorator(f: Callable[[Any], Any]):
        @wraps(f)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay

            while True:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded for {f.__name__}")
                        raise

                    logger.warning(
                        f"Retry {retries}/{max_retries} for {f.__name__} after error: {str(e)}")
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator
