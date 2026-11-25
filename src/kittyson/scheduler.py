"""Makes each day's cat and quote ahead of the day, so a request only reads what is there.

Once a day, at 23:00, tomorrow's are made. Once more when the server starts, for today's:
they are missing on the first start, or after a night the server was off. What fails is
tried again every ten minutes, so the evening's tries are over before the day begins, and
the person who runs the server is told (notify.py).
"""

import asyncio
import logging
from datetime import date, datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from kittyson import clock
from kittyson.notify import Notifier

log = logging.getLogger(__name__)


class Job(Protocol):
    name: str  # what the notice calls it

    async def make(self, day: date) -> None:
        """Make and save the day's. Does nothing when it is there; raises when it cannot be made."""
        ...


class Scheduler:
    AT = time(23, 0)          # when tomorrow's are made
    JOB_TIMEOUT = 5 * 60      # seconds one making may take
    RETRY = timedelta(minutes=10)  # between two tries
    MAX_TRIES = 6             # 23:00, 23:10, 23:20, 23:30, 23:40, 23:50. Then the day goes without

    def __init__(self, jobs: list[Job], notifier: Notifier | None, tz: str):
        self._jobs = jobs
        self._notifier = notifier
        self._tz = tz
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self.run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

    async def run(self) -> None:
        day = self.now().date()
        await self.make(day)  # today's, when the server starts without them
        while True:
            # On a start after 23:00 this time is already past, and tomorrow's are made right away.
            await self.sleep_until(datetime.combine(day, self.AT, ZoneInfo(self._tz)))
            day += timedelta(days=1)
            await self.make(day)

    async def make(self, day: date) -> None:
        """Have every job make the day's. What fails is tried again every RETRY, MAX_TRIES times in all."""
        jobs, start = self._jobs, self.now()
        for tries in range(1, self.MAX_TRIES + 1):
            if tries > 1:
                await self.sleep_until(start + self.RETRY * (tries - 1))
            jobs = [job for job in jobs if not await self._try(job, day, tries)]
            if not jobs:
                return

    async def _try(self, job: Job, day: date, tries: int) -> bool:
        """Whether the job made the day's."""
        try:
            await asyncio.wait_for(job.make(day), self.JOB_TIMEOUT)
            return True
        except Exception as exc:
            log.warning("%s of %s not made (try %s of %s): %r", job.name, day, tries, self.MAX_TRIES, exc)
            if tries in (1, self.MAX_TRIES):
                await self._notify(job, day, tries, exc)
            return False

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

    # The clock, in two methods, so that a test can put its own in their place.

    def now(self) -> datetime:
        return clock.now(self._tz)

    async def sleep_until(self, when: datetime) -> None:
        await asyncio.sleep(max(0.0, (when - self.now()).total_seconds()))
