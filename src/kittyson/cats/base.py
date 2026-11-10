"""Daily cat selection.

A Provider hands back raw image bytes plus an optional name/mood. DailyCat picks one
provider per day (date-seeded), crops the picture to a square, and caches the result as
data/cats/daily/YYYY-MM-DD.jpg + .json so the same day always shows the same cat.
"""

import asyncio
import json
import logging
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

from kittyson.images import save_square

log = logging.getLogger(__name__)

NAMES = [
    "참깨", "들깨", "호두", "모찌", "보리", "콩이", "나비", "치즈", "구름", "감자",
    "고구마", "두부", "밤이", "자몽", "쿠키", "망고", "코코", "단추", "탱자", "뭉치",
    "순두부", "메밀", "앙꼬", "율무", "깨비", "솜이", "연탄", "누룽지", "미소", "후추",
]

MOODS = [
    "sleepy", "grumpy", "zoomies", "hungry", "cozy", "curious", "chill", "dramatic",
    "loafing", "judging", "playful", "sassy", "melting", "alert", "purring", "snacky",
]


@dataclass
class CatPick:
    image: bytes
    name: str | None = None
    mood: str | None = None


class Provider(Protocol):
    key: str

    def weight(self) -> int:
        """0 means 'not available today' (e.g. an empty inbox)."""
        ...

    async def pick(self, day: date, rng: random.Random) -> CatPick: ...


@dataclass(frozen=True)
class CatOfTheDay:
    day: date
    path: Path
    name: str
    mood: str
    source: str

    @property
    def line(self) -> str:
        return f"{self.name} · {self.mood}"


class DailyCat:
    def __init__(self, providers: list[Provider], daily_dir: Path, size: int):
        self._providers = providers
        self._dir = daily_dir
        self._size = size
        self._lock = asyncio.Lock()

    def _paths(self, day: date) -> tuple[Path, Path]:
        stem = self._dir / day.isoformat()
        return stem.with_suffix(".jpg"), stem.with_suffix(".json")

    def cached(self, day: date) -> CatOfTheDay | None:
        jpg, meta = self._paths(day)
        if not (jpg.exists() and meta.exists()):
            return None
        info = json.loads(meta.read_text(encoding="utf-8"))
        return CatOfTheDay(day=day, path=jpg, name=info["name"], mood=info["mood"], source=info["source"])

    def latest(self) -> CatOfTheDay | None:
        """Most recent cached cat of any day. Used when every provider fails."""
        if not self._dir.exists():
            return None
        for meta in sorted(self._dir.glob("*.json"), reverse=True):
            try:
                found = self.cached(date.fromisoformat(meta.stem))
            except ValueError:
                continue
            if found:
                return found
        return None

    async def get(self, day: date) -> CatOfTheDay | None:
        if hit := self.cached(day):
            return hit
        async with self._lock:
            if hit := self.cached(day):  # someone else filled it while we waited
                return hit
            return await self._fetch(day)

    async def _fetch(self, day: date) -> CatOfTheDay | None:
        rng = random.Random(f"cat:{day.isoformat()}")
        name = rng.choice(NAMES)
        mood = rng.choice(MOODS)

        weighted = [(p, p.weight()) for p in self._providers]
        weighted = [(p, w) for p, w in weighted if w > 0]
        if not weighted:
            log.warning("no cat provider available")
            return self.latest()

        # Seeded choice first, then the rest in priority order as fallbacks.
        first = rng.choices([p for p, _ in weighted], weights=[w for _, w in weighted], k=1)[0]
        order = [first] + [p for p, _ in weighted if p is not first]

        jpg, meta = self._paths(day)
        for provider in order:
            try:
                pick = await provider.pick(day, rng)
                save_square(pick.image, self._size, jpg)
            except Exception as exc:
                log.warning("cat provider %s failed: %s", provider.key, exc)
                continue
            info = {
                "name": pick.name or name,
                "mood": pick.mood or mood,
                "source": provider.key,
            }
            meta.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
            log.info("cat of %s: %s · %s (%s)", day, info["name"], info["mood"], provider.key)
            return CatOfTheDay(day=day, path=jpg, name=info["name"], mood=info["mood"], source=provider.key)

        log.error("all cat providers failed for %s; reusing latest cached cat", day)
        return self.latest()
