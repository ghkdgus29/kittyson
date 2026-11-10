"""Pictures you dropped into data/cats/inbox/.

Optional data/cats/inbox/cats.json gives a name and mood per file:
[
  { "file": "sesame-01.jpg", "name": "참깨", "mood": "sleepy" }
]
Files not listed there get a date-seeded name and mood like any other provider.
"""

import json
import random
from datetime import date
from pathlib import Path

from kittyson.cats.base import CatPick

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

    def manifest(self) -> dict[str, dict]:
        path = self._inbox / "cats.json"
        if not path.exists():
            return {}
        entries = json.loads(path.read_text(encoding="utf-8"))
        return {e["file"]: e for e in entries if "file" in e}

    def weight(self) -> int:
        return self._weight if self.files() else 0

    async def pick(self, day: date, rng: random.Random) -> CatPick:
        files = self.files()
        if not files:
            raise FileNotFoundError(f"no pictures in {self._inbox}")
        chosen = rng.choice(files)
        info = self.manifest().get(chosen.name, {})
        return CatPick(image=chosen.read_bytes(), name=info.get("name"), mood=info.get("mood"))
