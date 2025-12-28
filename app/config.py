import os


def _safe_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _safe_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


MODEL_PATH = os.environ.get('MODEL_PATH')
N_THREADS = _safe_int('N_THREADS', 8)
CTX = _safe_int('CTX', 2048)
TEMP = _safe_float('TEMP', 0.0)
MAX_TOKENS = _safe_int('MAX_TOKENS', 512)
