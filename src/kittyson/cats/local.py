"""Pictures you dropped into data/cats/inbox/."""

import random
from datetime import date
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


class LocalProvider:
    key = "local"

    def __init__(self, inbox: Path, weight: int = 3):
        self._inbox = inbox
        self._weight = weight

    def files(self) -> list[Path]:
        if not self._inbox.exists():
            return []
        return sorted(p for p in self._inbox.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES and p.is_file())

    def weight(self) -> int:
        return self._weight if self.files() else 0

    async def pick(self, day: date, rng: random.Random) -> bytes:
        files = self.files()
        if not files:
            raise FileNotFoundError(f"no pictures in {self._inbox}")
        return rng.choice(files).read_bytes()
