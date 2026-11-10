import re
from datetime import date

from kittyson import clock
from kittyson.fortune import FORTUNES, fortune_for


def test_iso_seconds_has_offset_and_no_fraction():
    s = clock.iso_seconds(clock.now("Asia/Seoul"))
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00", s)


def test_weekday_ko():
    assert clock.weekday_ko(date(2026, 11, 10)) == "화요일"
    assert clock.weekday_ko(date(2026, 11, 15)) == "일요일"


def test_fortune_is_stable_per_day_and_from_list():
    d = date(2026, 11, 10)
    assert fortune_for(d) == fortune_for(d)
    assert fortune_for(d) in FORTUNES
    assert any(fortune_for(date(2026, 11, n)) != fortune_for(d) for n in range(11, 30))
