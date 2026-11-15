"""Daily cat selection.

A Provider hands back raw image bytes. DailyCat picks one provider per day (date-seeded),
crops the picture to a square, and reads off the photo the text colors that suit it (theme.py).
The result is kept as data/cats/daily/YYYY-MM-DD.jpg + .json, so the same day always shows
the same cat.
"""

import asyncio
import json
import logging
import random
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Protocol

from kittyson import theme as theming
from kittyson.images import save_square

log = logging.getLogger(__name__)

# Version of the saved .json. Bump it when what is read off the photo changes: the theme
# analysis or the fields themselves. A .json saved by another version does not count as
# cached, so that day's photo is read again (the photo itself stays).
VERSION = 4


class Provider(Protocol):
    key: str

    def weight(self) -> int:
        """0 means 'not available today' (e.g. an empty inbox)."""
        ...

    async def pick(self, day: date, rng: random.Random) -> bytes:
        """One cat picture, as the bytes of an image file."""
        ...


@dataclass(frozen=True)
class CatOfTheDay:
    day: date
    path: Path
    source: str
    theme: dict = field(default_factory=lambda: dict(theming.DEFAULT), compare=False)


class DailyCat:
    def __init__(self, providers: list[Provider], daily_dir: Path, size: int):
        self._providers = providers
        self._dir = daily_dir
        self._size = size
        self._lock = asyncio.Lock()

    def _paths(self, day: date) -> tuple[Path, Path]:
        stem = self._dir / day.isoformat()
        return stem.with_suffix(".jpg"), stem.with_suffix(".json")

    def _saved(self, day: date) -> dict | None:
        """The .json of a day whose photo is there too, whichever version saved it."""
        jpg, meta = self._paths(day)
        if not (jpg.exists() and meta.exists()):
            return None
        return json.loads(meta.read_text(encoding="utf-8"))

    def _cat(self, day: date, info: dict) -> CatOfTheDay:
        return CatOfTheDay(
            day=day,
            path=self._paths(day)[0],
            source=info["source"],
            theme=info.get("theme") or dict(theming.DEFAULT),
        )

    def cached(self, day: date) -> CatOfTheDay | None:
        """The day's cat, if this version saved it."""
        info = self._saved(day)
        if info is None or info.get("v") != VERSION:
            return None
        return self._cat(day, info)

    def latest(self) -> CatOfTheDay | None:
        """Most recent saved cat of any day. Used when every provider fails.

        Any version will do here: an older reading of the photo is better than no cat.
        """
        for meta in sorted(self._dir.glob("*.json"), reverse=True):
            try:
                day = date.fromisoformat(meta.stem)
            except ValueError:
                continue
            if info := self._saved(day):
                return self._cat(day, info)
        return None

    async def get(self, day: date) -> CatOfTheDay | None:
        if hit := self.cached(day):
            return hit
        async with self._lock:
            if hit := self.cached(day):  # someone else filled it while we waited
                return hit
            return await self._make(day)

    async def _make(self, day: date) -> CatOfTheDay | None:
        if old := self._saved(day):
            source = old["source"]  # saved by another version: keep the photo, read it again
        else:
            source = await self._fetch(day)
        if source is None:
            return self.latest()

        jpg, meta = self._paths(day)
        info = {"v": VERSION, "source": source, "theme": self._theme(jpg)}
        meta.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("cat of %s: from %s, %s text", day, source, info["theme"]["mode"])
        return self._cat(day, info)

    async def _fetch(self, day: date) -> str | None:
        """Save the day's photo. Returns the key of the provider it came from."""
        weighted = [(p, p.weight()) for p in self._providers]
        weighted = [(p, w) for p, w in weighted if w > 0]
        if not weighted:
            log.warning("no cat provider available")
            return None

        # Seeded choice first, then the rest in priority order as fallbacks.
        rng = random.Random(f"provider:{day.isoformat()}")
        first = rng.choices([p for p, _ in weighted], weights=[w for _, w in weighted], k=1)[0]
        order = [first] + [p for p, _ in weighted if p is not first]

        jpg, _ = self._paths(day)
        for provider in order:
            try:
                save_square(await provider.pick(day, rng), self._size, jpg)
            except Exception as exc:
                log.warning("cat provider %s failed: %s", provider.key, exc)
                continue
            return provider.key

        log.error("all cat providers failed for %s; reusing latest cached cat", day)
        return None

    @staticmethod
    def _theme(jpg: Path) -> dict:
        try:
            return theming.for_file(jpg)
        except Exception as exc:
            log.warning("theme analysis failed for %s: %s", jpg.name, exc)
            return dict(theming.DEFAULT)
