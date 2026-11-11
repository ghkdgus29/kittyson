import json
import random
from datetime import date
from pathlib import Path

import pytest
from PIL import Image

from kittyson.cats import CatPick, DailyCat, LocalProvider
from kittyson.images import square
from tests.conftest import make_jpeg


class FailingProvider:
    key = "boom"

    def weight(self) -> int:
        return 1

    async def pick(self, day: date, rng: random.Random) -> CatPick:
        raise RuntimeError("down")


class StaticProvider:
    key = "static"

    def __init__(self, data: bytes):
        self.data = data
        self.calls = 0

    def weight(self) -> int:
        return 1

    async def pick(self, day: date, rng: random.Random) -> CatPick:
        self.calls += 1
        return CatPick(image=self.data)


def test_square_crops_center_to_size():
    img = square(make_jpeg(640, 480), 256)
    assert img.size == (256, 256)


def test_local_provider_empty_inbox_has_zero_weight(inbox: Path):
    assert LocalProvider(inbox).weight() == 0


async def test_local_provider_uses_manifest(inbox: Path, jpeg_bytes: bytes):
    (inbox / "sesame.jpg").write_bytes(jpeg_bytes)
    (inbox / "cats.json").write_text(
        json.dumps([{"file": "sesame.jpg", "name": "참깨", "mood": "sleepy"}]), encoding="utf-8"
    )
    p = LocalProvider(inbox)
    assert p.weight() > 0
    pick = await p.pick(date(2026, 11, 10), random.Random(1))
    assert (pick.name, pick.mood) == ("참깨", "sleepy")
    assert pick.image == jpeg_bytes


async def test_daily_cat_is_cached_and_stable(tmp_path: Path, jpeg_bytes: bytes):
    provider = StaticProvider(jpeg_bytes)
    daily = DailyCat([provider], tmp_path / "daily", size=128)
    day = date(2026, 11, 10)

    first = await daily.get(day)
    second = await daily.get(day)
    assert first == second
    assert provider.calls == 1
    assert first.path.exists()
    assert Image.open(first.path).size == (128, 128)
    assert " · " in first.line

    # different day, different fetch (and possibly different name/mood)
    await daily.get(date(2026, 11, 11))
    assert provider.calls == 2


async def test_daily_cat_falls_through_to_next_provider(tmp_path: Path, jpeg_bytes: bytes):
    ok = StaticProvider(jpeg_bytes)
    daily = DailyCat([FailingProvider(), ok], tmp_path / "daily", size=64)
    cat = await daily.get(date(2026, 11, 10))
    assert cat is not None and cat.source == "static"


async def test_daily_cat_reuses_latest_when_all_fail(tmp_path: Path, jpeg_bytes: bytes):
    daily = DailyCat([StaticProvider(jpeg_bytes)], tmp_path / "daily", size=64)
    yesterday = await daily.get(date(2026, 11, 9))

    broken = DailyCat([FailingProvider()], tmp_path / "daily", size=64)
    today = await broken.get(date(2026, 11, 10))
    assert today == yesterday


async def test_daily_cat_none_when_nothing_available(tmp_path: Path):
    daily = DailyCat([FailingProvider()], tmp_path / "daily", size=64)
    assert await daily.get(date(2026, 11, 10)) is None


async def test_daily_cat_has_theme_and_backfills_old_meta(tmp_path: Path):
    daily = DailyCat([StaticProvider(make_jpeg(color=(250, 250, 250)))], tmp_path / "daily", size=64)
    day = date(2026, 11, 10)
    cat = await daily.get(day)
    assert cat.theme["mode"] == "dark"  # a white photo wants dark letters

    # A cat saved before themes existed gets one the next time it is read.
    meta = cat.path.with_suffix(".json")
    info = json.loads(meta.read_text(encoding="utf-8"))
    del info["theme"]
    meta.write_text(json.dumps(info), encoding="utf-8")
    assert daily.cached(day).theme == cat.theme
    assert "theme" in json.loads(meta.read_text(encoding="utf-8"))
