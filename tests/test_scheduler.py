import asyncio
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from kittyson.scheduler import Scheduler

TZ = "Asia/Seoul"
TODAY = date(2026, 11, 24)
TOMORROW = date(2026, 11, 25)


def at(hour: int, minute: int = 0, day: date = TODAY) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=ZoneInfo(TZ))


class FakeJob:
    """Makes a day once. The first `failures` tries raise."""

    def __init__(self, name: str = "고양이", failures: int = 0):
        self.name = name
        self.failures = failures
        self.tries: list[date] = []
        self.made: list[date] = []

    async def make(self, day: date) -> None:
        if day in self.made:
            return
        self.tries.append(day)
        if self.failures:
            self.failures -= 1
            raise RuntimeError("pixabay search answered 500")
        self.made.append(day)


class FakeNotifier:
    def __init__(self):
        self.sent: list[str] = []

    async def send(self, text: str) -> None:
        self.sent.append(text)


async def test_before_23_only_today_is_made_and_from_23_on_tomorrow_too():
    cat, quote = FakeJob("고양이"), FakeJob("명언")
    scheduler = Scheduler([cat, quote], None, TZ)

    await scheduler.tick(at(9))
    await scheduler.tick(at(22, 59))
    assert cat.made == [TODAY] and quote.made == [TODAY]

    await scheduler.tick(at(23))
    await scheduler.tick(at(23, 1))
    assert cat.made == [TODAY, TOMORROW] and quote.made == [TODAY, TOMORROW]

    await scheduler.tick(at(0, 1, TOMORROW))  # the day has begun, and it is all there
    assert cat.tries == [TODAY, TOMORROW]


async def test_a_failure_is_told_once_and_tried_again_every_ten_minutes():
    cat, notifier = FakeJob(failures=2), FakeNotifier()
    scheduler = Scheduler([cat], notifier, TZ)

    await scheduler.tick(at(10))
    assert len(cat.tries) == 1 and len(notifier.sent) == 1
    assert "2026-11-24 고양이" in notifier.sent[0] and "pixabay search answered 500" in notifier.sent[0]

    await scheduler.tick(at(10, 9))
    assert len(cat.tries) == 1                # ten minutes are not over
    await scheduler.tick(at(10, 10))
    assert len(cat.tries) == 2                # the second failure
    await scheduler.tick(at(10, 19))
    assert len(cat.tries) == 2                # ten minutes again, no longer
    await scheduler.tick(at(10, 20))
    assert cat.made == [TODAY]
    assert len(notifier.sent) == 1            # only the first failure was told


async def test_after_the_last_try_the_day_is_left_alone_and_that_is_told_too():
    cat, notifier = FakeJob(failures=100), FakeNotifier()
    scheduler = Scheduler([cat], notifier, TZ)

    now = at(23, 0, TODAY - timedelta(days=1))  # 23:00 the evening before, for TODAY
    for _ in range(24 * 60):
        before = len([day for day in cat.tries if day == TODAY])
        await scheduler.tick(now)
        if len([day for day in cat.tries if day == TODAY]) > before:
            assert now.date() < TODAY           # every try is over before the day begins
        now += timedelta(minutes=1)

    todays = [day for day in cat.tries if day == TODAY]
    assert len(todays) == Scheduler.MAX_TRIES
    notices = [text for text in notifier.sent if "2026-11-24" in text]
    assert len(notices) == 2 and "더 시도하지 않습니다" in notices[1]


async def test_one_job_failing_does_not_keep_the_other_from_being_made():
    cat, quote = FakeJob("고양이", failures=1), FakeJob("명언")
    await Scheduler([cat, quote], None, TZ).tick(at(10))  # and no notifier is fine
    assert cat.made == [] and quote.made == [TODAY]


async def test_a_job_that_hangs_is_cut_off(monkeypatch: pytest.MonkeyPatch):
    class Hanging(FakeJob):
        async def make(self, day: date) -> None:
            await asyncio.sleep(60)

    monkeypatch.setattr(Scheduler, "JOB_TIMEOUT", 0.01)
    notifier = FakeNotifier()
    await Scheduler([Hanging()], notifier, TZ).tick(at(10))
    assert "TimeoutError" in notifier.sent[0]


async def test_started_it_makes_today_right_away_and_stops_when_told():
    cat = FakeJob()
    scheduler = Scheduler([cat], None, TZ)
    scheduler.start()
    await asyncio.sleep(0.01)
    await scheduler.stop()
    assert cat.made[0] == datetime.now(ZoneInfo(TZ)).date()
