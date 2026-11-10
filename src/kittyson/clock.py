"""Server time in the configured timezone."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

WEEKDAYS_KO = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


def now(tz: str) -> datetime:
    return datetime.now(ZoneInfo(tz))


def today(tz: str) -> date:
    return now(tz).date()


def iso_seconds(dt: datetime) -> str:
    """2026-11-10T14:01:53+09:00"""
    return dt.isoformat(timespec="seconds")


def weekday_ko(d: date) -> str:
    return WEEKDAYS_KO[d.weekday()]
