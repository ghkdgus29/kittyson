import asyncio
import re
import time
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kittyson import clock, deps
from kittyson.cats import CatStore, DailyCat
from kittyson.config import settings
from kittyson.main import app
from kittyson.quote import DailyQuote, Quote, fallback
from kittyson.store import DayStore
from tests.conftest import FakeSource, FakeWriter

WIDGET_KEYS = ["time", "date", "weekday", "weather", "quote", "by"]
WEATHER = "☁️ 11° ↑14 ↓6"


class FakeWeather:
    async def line(self) -> str:
        return WEATHER


def today() -> date:
    return clock.today(settings.tz)


def make(day: date) -> None:
    """Put the day's cat and quote into the data folder, as the scheduler would have before a request."""

    async def both():
        await DailyCat(FakeSource(), CatStore(settings.cats_daily), 64).make(day)
        await DailyQuote(FakeWriter(), DayStore(settings.quotes, Quote)).make(day)

    asyncio.run(both())


def nothing_can_be_made(monkeypatch: pytest.MonkeyPatch) -> None:
    down = [RuntimeError("down")] * 2  # late in the evening the scheduler asks for two days
    monkeypatch.setattr(deps, "cat_source", lambda: FakeSource(*down))
    monkeypatch.setattr(deps, "quote_writer", lambda: FakeWriter(*down))


@pytest.fixture
def data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """An empty data folder, and fakes in place of all that reaches outside."""
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(deps, "cat_source", FakeSource)
    monkeypatch.setattr(deps, "quote_writer", FakeWriter)
    monkeypatch.setattr(deps, "notifier", lambda: None)
    app.dependency_overrides[deps.get_weather_service] = FakeWeather
    yield tmp_path
    app.dependency_overrides.clear()


@pytest.fixture
def client(data: Path):
    make(today())
    with TestClient(app) as c:
        yield c


def test_today_is_the_lines_and_the_cat_in_one_answer(client: TestClient):
    r = client.get("/api/today")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    body = r.json()
    assert list(body) == ["widget", "cat"]

    widget = body["widget"]
    assert list(widget) == WIDGET_KEYS
    assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", widget["time"])
    assert widget["date"] == today().isoformat()
    assert widget["weather"] == WEATHER
    assert (widget["quote"], widget["by"]) == (FakeWriter.LINE, FakeWriter.BY)

    cat = body["cat"]
    assert list(cat) == ["day", "source", "theme"]  # which photos were used or skipped stays on the server
    assert (cat["day"], cat["source"]) == (today().isoformat(), "fake")
    theme = cat["theme"]
    assert theme["mode"] in ("light", "dark")
    for key in ("punct", "key", "str", "halo"):
        assert re.fullmatch(r"#[0-9a-f]{6}", theme[key])
    assert 0 < theme["halo_alpha"] <= 1


def test_cat_photo_is_a_jpeg(client: TestClient):
    r = client.get("/cat/today.jpg")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert r.content[:2] == b"\xff\xd8"


def test_before_anything_is_made_there_is_the_list_quote_and_no_cat(data: Path, monkeypatch: pytest.MonkeyPatch):
    nothing_can_be_made(monkeypatch)
    with TestClient(app) as client:
        body = client.get("/api/today").json()
        assert body["cat"] is None
        assert (body["widget"]["quote"], body["widget"]["by"]) == (fallback(today()).line, fallback(today()).by)
        assert client.get("/cat/today.jpg").status_code == 503
    assert not list(data.glob("cats/daily/*")) and not list(data.glob("quotes/*"))  # a request makes nothing


def test_a_day_whose_cat_could_not_be_made_shows_the_one_before(data: Path, monkeypatch: pytest.MonkeyPatch):
    yesterday = today() - timedelta(days=1)
    make(yesterday)
    nothing_can_be_made(monkeypatch)
    with TestClient(app) as client:
        body = client.get("/api/today").json()
        assert body["cat"]["day"] == yesterday.isoformat()
        assert body["widget"]["date"] == today().isoformat()
        assert client.get("/cat/today.jpg").status_code == 200


def test_started_with_nothing_the_app_makes_today_by_itself(data: Path):
    with TestClient(app) as client:
        for _ in range(200):
            body = client.get("/api/today").json()
            if body["cat"] and body["widget"]["quote"] == FakeWriter.LINE:
                break
            time.sleep(0.01)
        assert body["cat"]["day"] == today().isoformat()
        assert body["widget"]["quote"] == FakeWriter.LINE


def test_index_and_static(client: TestClient):
    assert "kittyson" in client.get("/").text
    assert "/api/today" in client.get("/static/app.js").text
    assert client.get("/healthz").json()["ok"] is True


def test_dependencies_are_built_once_and_dropped_on_shutdown(data: Path):
    built = (deps.get_scheduler, deps.get_daily_cat, deps.get_daily_quote, deps.get_weather_service, deps.get_http_client)
    with TestClient(app):
        assert deps.get_daily_cat() is deps.get_daily_cat()
        assert deps.get_scheduler() is deps.get_scheduler()
        assert all(get.cache_info().currsize == 1 for get in built)
    assert all(get.cache_info().currsize == 0 for get in built)
