from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from .config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def local_today() -> date:
    return datetime.now(ZoneInfo(settings.timezone)).date()
