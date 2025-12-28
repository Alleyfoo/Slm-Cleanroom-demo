import sys
import uuid
from typing import Optional, Tuple

from loguru import logger

# Configure a single JSON logger sink
logger.remove()
logger.add(sys.stdout, serialize=True, backtrace=False, diagnose=False)


def get_logger(correlation_id: Optional[str] = None) -> Tuple["logger", str]:
    """Return a logger bound with a correlation id."""
    cid = correlation_id or str(uuid.uuid4())
    return logger.bind(correlation_id=cid), cid
