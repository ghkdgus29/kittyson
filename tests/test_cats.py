import json
import random
from datetime import date
from pathlib import Path

from PIL import Image

from kittyson.cats import DailyCat, LocalProvider, base
from kittyson.images import square
from tests.conftest import make_jpeg

DAY = date(2026, 11, 11)


class FailingProvider:
    key = "boom"

    def weight(self) -> int:
        return 1

    async def pick(self, day: date, rng: random.Random) -> bytes:
        raise RuntimeError("down")


class StaticProvider:
    key = "static"

    def __init__(self, data: bytes):
        self.data = data
        self.calls = 0

    def weight(self) -> int:
        return 1

    async def pick(self, day: date, rng: random.Random) -> bytes:
        self.calls += 1
        return self.data


def saved(cat) -> dict:
    return json.loads(cat.path.with_suffix(".json").read_text(encoding="utf-8"))


def test_square_crops_center_to_size():
    img = square(make_jpeg(640, 480), 256)
    assert img.size == (256, 256)


def test_local_provider_empty_inbox_has_zero_weight(inbox: Path):
    assert LocalProvider(inbox).weight() == 0


async def test_local_provider_picks_a_picture_from_the_inbox(inbox: Path, jpeg_bytes: bytes):
    (inbox / "sesame.jpg").write_bytes(jpeg_bytes)
    (inbox / "notes.txt").write_text("not a picture", encoding="utf-8")
    p = LocalProvider(inbox)
    assert p.weight() > 0
    assert await p.pick(date(2026, 11, 10), random.Random(1)) == jpeg_bytes


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

    # different day, different fetch
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


async def test_daily_cat_has_a_theme_read_off_the_photo(tmp_path: Path):
    daily = DailyCat([StaticProvider(make_jpeg(color=(250, 250, 250)))], tmp_path / "daily", size=64)
    cat = await daily.get(DAY)
    assert cat.theme["mode"] == "dark"  # a white photo wants dark letters
    assert saved(cat)["v"] == base.VERSION


async def test_cat_saved_by_another_version_is_read_again_from_the_same_photo(tmp_path: Path, jpeg_bytes: bytes):
    provider = StaticProvider(jpeg_bytes)
    daily = DailyCat([provider], tmp_path / "daily", size=64)
    cat = await daily.get(DAY)
    photo = cat.path.read_bytes()

    meta = cat.path.with_suffix(".json")
    meta.write_text(json.dumps({**saved(cat), "v": base.VERSION - 1, "theme": {"mode": "old"}}), encoding="utf-8")
    assert daily.cached(DAY) is None  # another version's .json is not a cache hit

    cat = await daily.get(DAY)
    assert cat.theme["mode"] in ("light", "dark")
    assert provider.calls == 1 and cat.path.read_bytes() == photo  # no new photo was fetched
    assert saved(cat)["v"] == base.VERSION
    assert daily.cached(DAY) == cat


async def test_latest_takes_a_cat_saved_by_an_older_version(tmp_path: Path, jpeg_bytes: bytes):
    daily = DailyCat([StaticProvider(jpeg_bytes)], tmp_path / "daily", size=64)
    cat = await daily.get(date(2026, 11, 9))
    old = {"name": "탱자", "mood": "snacky", "source": "cataas"}  # no version, no theme
    cat.path.with_suffix(".json").write_text(json.dumps(old), encoding="utf-8")

    broken = DailyCat([FailingProvider()], tmp_path / "daily", size=64)
    assert (await broken.get(DAY)).path == cat.path
