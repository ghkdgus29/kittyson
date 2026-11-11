import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from kittyson import clock


def test_time_and_date_strings():
    dt = datetime(2026, 11, 10, 9, 5, 7, tzinfo=ZoneInfo("Asia/Seoul"))
    assert clock.time_str(dt) == "09:05:07"
    assert clock.date_str(dt) == "2026-11-10"
    assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", clock.time_str(clock.now("Asia/Seoul")))


def test_weekday_ko():
    assert clock.weekday_ko(date(2026, 11, 10)) == "화요일"
    assert clock.weekday_ko(date(2026, 11, 15)) == "일요일"
