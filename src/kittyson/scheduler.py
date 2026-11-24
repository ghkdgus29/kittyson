"""Makes each day's cat and quote ahead of the day, so a request only reads what is there.

From 23:00 on, tomorrow's are made. Today's are made too whenever they are missing: on the
first start, or after a night the server was off. What fails is tried again every ten minutes,
so the evening's tries are over before the day begins, and the person who runs the server is
told (notify.py).
"""

import asyncio
import logging
from datetime import date, datetime, time, timedelta
from typing import Protocol

from kittyson import clock
from kittyson.notify import Notifier

log = logging.getLogger(__name__)


class Job(Protocol):
    name: str  # what the notice calls it

    async def make(self, day: date) -> None:
        """Make and save the day's. Does nothing when it is there; raises when it cannot be made."""
        ...


class Scheduler:
    AT = time(23, 0)          # tomorrow's are made from this time on
    EVERY = 60                # seconds between two looks at the clock
    JOB_TIMEOUT = 5 * 60      # seconds one making may take
    RETRY = timedelta(minutes=10)  # between two tries
    MAX_TRIES = 6             # 23:00, 23:10, 23:20, 23:30, 23:40, 23:50. Then the day goes without

    def __init__(self, jobs: list[Job], notifier: Notifier | None, tz: str):
        self._jobs = jobs
        self._notifier = notifier
        self._tz = tz
        self._failed: dict[tuple[str, date], tuple[int, datetime]] = {}  # tries so far, and when the last one was
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

    async def _run(self) -> None:
        while True:
            try:
                await self.tick(clock.now(self._tz))
            except Exception:
                log.exception("scheduler tick failed")
            await asyncio.sleep(self.EVERY)

    async def tick(self, now: datetime) -> None:
        """Make what should be there at `now` and is not."""
        today = now.date()
        days = [today, today + timedelta(days=1)] if now.time() >= self.AT else [today]
        self._failed = {key: tries for key, tries in self._failed.items() if key[1] >= today}
        for day in days:
            for job in self._jobs:
                await self._make(job, day, now)

    async def _make(self, job: Job, day: date, now: datetime) -> None:
        tries, last = self._failed.get((job.name, day), (0, now))
        if tries >= self.MAX_TRIES or (tries and now - last < self.RETRY):
            return
        try:
            await asyncio.wait_for(job.make(day), self.JOB_TIMEOUT)
        except Exception as exc:
            tries += 1
            self._failed[(job.name, day)] = (tries, now)
            log.warning("%s of %s not made (try %s of %s): %r", job.name, day, tries, self.MAX_TRIES, exc)
            if tries in (1, self.MAX_TRIES):
                await self._notify(job, day, tries, exc)

    async def _notify(self, job: Job, day: date, tries: int, exc: Exception) -> None:
        if not self._notifier:
            return
        if tries < self.MAX_TRIES:
            minutes = int(self.RETRY.total_seconds() // 60)
            ending = f"{minutes}분 간격으로 {self.MAX_TRIES - tries}번 더 시도합니다."
        else:
            ending = f"{tries}번 모두 실패해서 더 시도하지 않습니다. 이 날은 가장 최근 고양이, 목록에 있는 명언이 대신 나옵니다."
        reason = f"{type(exc).__name__}: {exc}"[:300]
        await self._notifier.send(f"🐱 kittyson: {day} {job.name} 만들기에 실패했어요.\n{reason}\n{ending}")
