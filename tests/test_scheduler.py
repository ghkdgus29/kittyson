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


class Clocked(Scheduler):
    """A scheduler with a clock the test owns: sleeping until a time puts the clock there at once.
    A sleep that would end after `until` ends the run instead, the way stop() does."""

    def __init__(self, jobs, notifier, start: datetime, until: datetime | None = None):
        super().__init__(jobs, notifier, TZ)
        self.clock = start
        self.until = until
        self.slept: list[datetime] = []  # every time it slept until

    def now(self) -> datetime:
        return self.clock

    async def sleep_until(self, when: datetime) -> None:
        if self.until and when > self.until:
            raise asyncio.CancelledError
        self.slept.append(when)
        self.clock = max(self.clock, when)


async def test_today_is_made_at_the_start_and_then_tomorrow_once_each_evening_at_23():
    cat, quote = FakeJob("고양이"), FakeJob("명언")
    scheduler = Clocked([cat, quote], None, start=at(9), until=at(23, day=TOMORROW))

    with pytest.raises(asyncio.CancelledError):
        await scheduler.run()

    days = [TODAY, TOMORROW, TOMORROW + timedelta(days=1)]
    assert cat.tries == days and quote.tries == days          # each day asked for once, no more
    assert scheduler.slept == [at(23), at(23, day=TOMORROW)]  # and nothing is looked at in between


async def test_started_after_23_tomorrow_is_made_right_away():
    cat = FakeJob()
    scheduler = Clocked([cat], None, start=at(23, 30), until=at(23, 30))

    with pytest.raises(asyncio.CancelledError):
        await scheduler.run()

    assert cat.made == [TODAY, TOMORROW] and scheduler.clock == at(23, 30)


async def test_a_failure_is_told_once_and_tried_again_every_ten_minutes():
    cat, notifier = FakeJob(failures=2), FakeNotifier()
    scheduler = Clocked([cat], notifier, start=at(23))

    await scheduler.make(TOMORROW)

    assert scheduler.slept == [at(23, 10), at(23, 20)]
    assert cat.tries == [TOMORROW] * 3 and cat.made == [TOMORROW]
    assert len(notifier.sent) == 1  # only the first failure was told
    assert "2026-11-25 고양이" in notifier.sent[0] and "pixabay search answered 500" in notifier.sent[0]
    assert "10분 간격으로 5번 더" in notifier.sent[0]


async def test_after_the_last_try_the_day_is_left_alone_and_that_is_told_too():
    cat, notifier = FakeJob(failures=100), FakeNotifier()
    scheduler = Clocked([cat], notifier, start=at(23))

    await scheduler.make(TOMORROW)

    assert len(cat.tries) == Scheduler.MAX_TRIES
    assert scheduler.slept == [at(23, minute) for minute in (10, 20, 30, 40, 50)]  # over before the day begins
    assert len(notifier.sent) == 2 and "더 시도하지 않습니다" in notifier.sent[1]


async def test_one_job_failing_does_not_keep_the_other_from_being_made():
    cat, quote = FakeJob("고양이", failures=1), FakeJob("명언")
    await Clocked([cat, quote], None, start=at(23)).make(TOMORROW)  # and no notifier is fine
    assert cat.tries == [TOMORROW] * 2 and cat.made == [TOMORROW]
    assert quote.tries == [TOMORROW]  # made at the first try, and not asked again


async def test_a_job_that_hangs_is_cut_off(monkeypatch: pytest.MonkeyPatch):
    class Hanging(FakeJob):
        async def make(self, day: date) -> None:
            await asyncio.sleep(60)

    monkeypatch.setattr(Scheduler, "JOB_TIMEOUT", 0.01)
    notifier = FakeNotifier()
    await Clocked([Hanging()], notifier, start=at(23)).make(TOMORROW)
    assert "TimeoutError" in notifier.sent[0]


async def test_started_it_makes_today_right_away_and_stops_when_told():
    cat = FakeJob()
    scheduler = Scheduler([cat], None, TZ)
    scheduler.start()
    await asyncio.sleep(0.01)
    await scheduler.stop()
    assert cat.made[0] == datetime.now(ZoneInfo(TZ)).date()
