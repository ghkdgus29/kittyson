"""Server time in the configured timezone."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

WEEKDAYS_KO = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


def now(tz: str) -> datetime:
    return datetime.now(ZoneInfo(tz))


def today(tz: str) -> date:
    return now(tz).date()


def time_str(dt: datetime) -> str:
    """14:01:53 (24-hour)"""
    return dt.strftime("%H:%M:%S")


def date_str(dt: datetime) -> str:
    """2026-11-10"""
    return dt.date().isoformat()


def weekday_ko(d: date) -> str:
    return WEEKDAYS_KO[d.weekday()]
