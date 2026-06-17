import time
import random
from functools import wraps
from utils.logger import get_logger
from config.settings import MAX_RETRIES

logger = get_logger("retry_service")


def retry(max_retries: int = MAX_RETRIES, delay: float = 2.0, backoff: float = 2.0):
    """Decorator retry với exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            while attempt < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt == max_retries:
                        logger.error(f"[{func.__name__}] Thất bại sau {max_retries} lần: {e}")
                        raise
                    jitter = random.uniform(0, 0.5)
                    wait = current_delay + jitter
                    logger.warning(f"[{func.__name__}] Lần {attempt}/{max_retries} thất bại: {e}. Thử lại sau {wait:.1f}s")
                    time.sleep(wait)
                    current_delay *= backoff
        return wrapper
    return decorator