import uuid
from datetime import datetime


def new_id() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.utcnow()


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
