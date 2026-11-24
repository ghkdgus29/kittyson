import json
from datetime import date
from pathlib import Path

import pytest
from PIL import Image

from kittyson.cats import Cat, CatStore, DailyCat, Photo
from kittyson.images import square
from kittyson.theme import Theme
from tests.conftest import FakeSource, make_jpeg

DAY = date(2026, 11, 11)
YESTERDAY = date(2026, 11, 10)


def daily(tmp_path: Path, source: FakeSource, size: int = 64) -> DailyCat:
    return DailyCat(source, CatStore(tmp_path), size)


def test_square_crops_center_to_size():
    img = square(make_jpeg(640, 480), 256)
    assert img.size == (256, 256)


async def test_a_made_cat_is_a_square_photo_and_a_record_next_to_it(tmp_path: Path, jpeg_bytes: bytes):
    cats = daily(tmp_path, FakeSource(Photo(id="42", data=jpeg_bytes, skipped=("7",))), size=128)
    assert cats.get(DAY) is None

    await cats.make(DAY)
    cat = cats.get(DAY)
    assert (cat.day, cat.source, cat.id, cat.skipped) == (DAY, "fake", "42", ["7"])
    assert cats.photo(cat) == tmp_path / "2026-11-11.jpg"
    assert Image.open(cats.photo(cat)).size == (128, 128)

    saved = json.loads((tmp_path / "2026-11-11.json").read_text(encoding="utf-8"))
    assert saved["id"] == "42" and saved["theme"]["str"] == cat.theme.string
    assert "v" not in saved  # no versions: a record is its fields


async def test_a_day_is_made_once_and_stays_the_same_after_a_restart(tmp_path: Path):
    source = FakeSource()
    cats = daily(tmp_path, source)
    await cats.make(DAY)
    await cats.make(DAY)
    assert len(source.seen) == 1

    again = daily(tmp_path, source)
    await again.make(DAY)
    assert len(source.seen) == 1 and again.get(DAY) == cats.get(DAY)


async def test_the_theme_is_read_off_the_photo(tmp_path: Path):
    cats = daily(tmp_path, FakeSource(Photo(id="1", data=make_jpeg(color=(250, 250, 250)))))
    await cats.make(DAY)
    assert cats.get(DAY).theme.mode == "dark"  # a white photo wants dark letters


async def test_the_source_is_told_every_photo_used_or_skipped_so_far(tmp_path: Path, jpeg_bytes: bytes):
    source = FakeSource(
        Photo(id="10", data=jpeg_bytes, skipped=("8", "9")),
        Photo(id="11", data=jpeg_bytes),
        Photo(id="12", data=jpeg_bytes),
    )
    cats = daily(tmp_path, source)
    for day in (date(2026, 11, 9), YESTERDAY, DAY):
        await cats.make(day)
    assert source.seen == [set(), {"8", "9", "10"}, {"8", "9", "10", "11"}]


async def test_a_day_without_a_cat_shows_the_most_recent_one(tmp_path: Path):
    cats = daily(tmp_path, FakeSource(Photo(id="1", data=make_jpeg()), RuntimeError("down")))
    await cats.make(YESTERDAY)
    with pytest.raises(RuntimeError):
        await cats.make(DAY)

    cat = cats.get(DAY)
    assert cat.day == YESTERDAY and cats.photo(cat).exists()
    assert cats.get(YESTERDAY - (DAY - YESTERDAY)) is None  # nothing before the first cat


def test_cats_saved_before_there_were_ids_are_still_read(tmp_path: Path, jpeg_bytes: bytes):
    theme = {"mode": "dark", "punct": "#101010", "key": "#054565", "str": "#623705", "halo": "#ffffff",
             "halo_alpha": 0.86, "luma": [0.177, 0.413, 0.863]}  # fmt: skip
    old = {
        "2026-11-09": {"name": "탱자", "mood": "snacky", "source": "cataas"},
        "2026-11-10": {"v": 4, "source": "pixabay", "theme": theme},
    }
    for day, record in old.items():
        (tmp_path / f"{day}.json").write_text(json.dumps(record), encoding="utf-8")
        (tmp_path / f"{day}.jpg").write_bytes(jpeg_bytes)
    store = CatStore(tmp_path)

    assert store.load(date(2026, 11, 9)) == Cat(day=date(2026, 11, 9), source="cataas")
    cat = store.load(YESTERDAY)
    assert cat.source == "pixabay" and cat.id == "" and cat.theme == Theme.model_validate(theme)
    assert store.seen() == set()  # a cat without an id rules no photo out


def test_a_record_that_cannot_be_read_is_no_cat(tmp_path: Path):
    (tmp_path / "2026-11-11.json").write_text("{half a file", encoding="utf-8")
    (tmp_path / "2026-11-10.json").write_text(json.dumps({"theme": "no source"}), encoding="utf-8")
    (tmp_path / "notes.json").write_text("{}", encoding="utf-8")
    store = CatStore(tmp_path)
    assert store.load(DAY) is None and store.load(YESTERDAY) is None
    assert store.before(date(2026, 12, 1)) == []


async def test_before_lists_earlier_days_newest_first(tmp_path: Path):
    cats = daily(tmp_path, FakeSource())
    days = [date(2026, 11, n) for n in (8, 9, 10, 11)]
    for day in days:
        await cats.make(day)
    store = CatStore(tmp_path)
    assert [cat.day for cat in store.before(DAY)] == [days[2], days[1], days[0]]
    assert [cat.day for cat in store.before(DAY, 2)] == [days[2], days[1]]
    assert store.days() == days[::-1]
