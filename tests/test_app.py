import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kittyson import config
from kittyson.weather import Weather, WeatherService
from tests.conftest import make_jpeg

EXPECTED_KEYS = ["meow", "time", "date", "weekday", "cat", "weather", "fortune"]


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    inbox = tmp_path / "cats" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "a.jpg").write_bytes(make_jpeg())

    monkeypatch.setenv("KITTYSON_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KITTYSON_CAT_SOURCES", "local")
    monkeypatch.setenv("KITTYSON_CAT_SIZE", "64")
    config.get_settings.cache_clear()

    async def fake_current(self):
        return Weather(temp=11.4, high=14, low=6, code=3, is_day=True)

    monkeypatch.setattr(WeatherService, "current", fake_current)

    from kittyson.main import app

    with TestClient(app) as c:
        yield c
    config.get_settings.cache_clear()


def test_widget_shape_and_order(client: TestClient):
    r = client.get("/api/widget")
    assert r.status_code == 200
    body = r.json()
    assert list(body.keys()) == EXPECTED_KEYS
    assert body["meow"].startswith("🐱 kittyson")
    assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", body["time"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", body["date"])
    assert body["weather"] == "☁️ 11° 흐림 ↑14 ↓6"
    assert " · " in body["cat"]
    assert r.headers["cache-control"] == "no-store"


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
    assert f'{body["name"]} · {body["mood"]}' == client.get("/api/widget").json()["cat"]
    theme = body["theme"]
    assert theme["mode"] in ("light", "dark")
    for key in ("punct", "key", "str", "num", "halo"):
        assert re.fullmatch(r"#[0-9a-f]{6}", theme[key])
    assert 0 < theme["halo_alpha"] <= 1


def test_index_and_static(client: TestClient):
    assert "kittyson" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/healthz").json()["ok"] is True
