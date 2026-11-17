import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kittyson.cats import DailyCat, LocalProvider
from kittyson.config import settings
from kittyson.deps import get_daily_cat, get_daily_quote, get_weather_service
from kittyson.main import app
from kittyson.quote import QUOTES, DailyQuote
from tests.conftest import make_jpeg

EXPECTED_KEYS = ["time", "date", "weekday", "weather", "quote"]
WRITTEN = "수요일의 반은 이미 내 편이다"


class FakeWeather:
    async def line(self) -> str:
        return "☁️ 11° ↑14 ↓6"


class FakeWriter:
    async def write(self, day, recent) -> tuple[str, str]:
        return WRITTEN, "아무개"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    inbox = tmp_path / "cats" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "a.jpg").write_bytes(make_jpeg())
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    # No network: the cat comes from the inbox only; the weather and the quote are canned.
    cats = DailyCat([LocalProvider(inbox)], tmp_path / "cats" / "daily", size=64)
    quotes = DailyQuote(FakeWriter(), tmp_path / "quotes")
    app.dependency_overrides[get_daily_cat] = lambda: cats
    app.dependency_overrides[get_daily_quote] = lambda: quotes
    app.dependency_overrides[get_weather_service] = FakeWeather

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_widget_shape_and_order(client: TestClient):
    r = client.get("/api/widget")
    assert r.status_code == 200
    body = r.json()
    assert list(body.keys()) == EXPECTED_KEYS
    assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", body["time"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", body["date"])
    assert body["weather"] == "☁️ 11° ↑14 ↓6"
    assert body["quote"] in QUOTES  # the written line is not there yet on the first request
    assert r.headers["cache-control"] == "no-store"


def test_widget_shows_the_written_quote_once_it_is_there(client: TestClient):
    lines = [client.get("/api/widget").json()["quote"] for _ in range(5)]
    assert lines[0] in QUOTES
    assert lines[-1] == WRITTEN


def test_cat_image_is_square_jpeg(client: TestClient):
    r = client.get("/cat/today.jpg")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert r.content[:2] == b"\xff\xd8"


def test_cat_meta_carries_theme(client: TestClient):
    r = client.get("/cat/today.json")
    assert r.status_code == 200
    body = r.json()
    assert body["date"] == client.get("/api/widget").json()["date"]
    assert body["source"] == "local"
    theme = body["theme"]
    assert theme["mode"] in ("light", "dark")
    for key in ("punct", "key", "str", "halo"):
        assert re.fullmatch(r"#[0-9a-f]{6}", theme[key])
    assert 0 < theme["halo_alpha"] <= 1


def test_index_and_static(client: TestClient):
    assert "kittyson" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/healthz").json()["ok"] is True


def test_dependencies_are_built_once_and_dropped_on_shutdown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    with TestClient(app):
        assert get_daily_cat() is get_daily_cat()
        assert get_weather_service() is get_weather_service()
        assert (tmp_path / "cats" / "inbox").is_dir()
    assert get_daily_cat.cache_info().currsize == 0
    assert get_weather_service.cache_info().currsize == 0
