"""The cat of each day: one photo, cropped to a square, with the text colors that suit it.

Kept as data/cats/daily/YYYY-MM-DD.jpg + .json. A day's cat is made once, ahead of the day
(scheduler.py), and does not change after that. No photo is used twice: each cat keeps the
id its photo has at the source, and a new photo is picked among the ids not seen yet.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

from kittyson import theme as theming
from kittyson.images import jpeg, square
from kittyson.store import DayRecord, DayStore, write
from kittyson.theme import Theme

log = logging.getLogger(__name__)


class Cat(DayRecord):
    source: str                # where the photo came from: "pixabay"
    id: str = ""               # the photo's id there. "" for cats saved before ids were kept
    skipped: list[str] = []    # ids looked at on the way to this photo that turned out not to be cats
    theme: Theme = Theme()


@dataclass(frozen=True)
class Photo:
    id: str
    data: bytes                     # an image file, as downloaded
    skipped: tuple[str, ...] = ()


class Source(Protocol):
    key: str

    async def pick(self, seen: set[str]) -> Photo:
        """A cat photo whose id is not in `seen`."""
        ...


class CatStore(DayStore[Cat]):
    def __init__(self, directory: Path):
        super().__init__(directory, Cat)

    def photo(self, day: date) -> Path:
        return self.path(day, ".jpg")

    def save_with_photo(self, cat: Cat, photo: bytes) -> None:
        write(self.photo(cat.day), photo)  # the photo first: a saved cat always has one
        self.save(cat)

    def seen(self) -> set[str]:
        """Every photo id used or skipped so far."""
        cats = [cat for day in self.days() if (cat := self.load(day))]
        return {id for cat in cats for id in (cat.id, *cat.skipped) if id}


class DailyCat:
    name = "고양이"

    def __init__(self, source: Source, store: CatStore, size: int):
        self._source = source
        self._store = store
        self._size = size

    def get(self, day: date) -> Cat | None:
        """The day's cat. While it is not there, the most recent one before it."""
        return self._store.load(day) or next(iter(self._store.before(day, 1)), None)

    def photo(self, cat: Cat) -> Path:
        return self._store.photo(cat.day)

    async def make(self, day: date) -> None:
        """Pick and save the day's cat. Does nothing when the day has one."""
        if self._store.load(day):
            return
        photo = await self._source.pick(self._store.seen())
        # Decoding, cropping and measuring a photo keeps a CPU busy: not on the event loop.
        cat = await asyncio.to_thread(self._save, day, photo)
        log.info("cat of %s: %s photo %s, %s text", day, cat.source, cat.id, cat.theme.mode)

    def _save(self, day: date, photo: Photo) -> Cat:
        image = square(photo.data, self._size)
        cat = Cat(
            day=day,
            source=self._source.key,
            id=photo.id,
            skipped=list(photo.skipped),
            theme=theming.analyze(image),
        )
        self._store.save_with_photo(cat, jpeg(image))
        return cat
