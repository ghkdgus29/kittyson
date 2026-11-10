"""FastAPI app: the screen, the JSON, and today's cat."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from kittyson import __version__, clock
from kittyson.cats import CataasProvider, DailyCat, LocalProvider, Provider
from kittyson.config import Settings, get_settings
from kittyson.fortune import fortune_for
from kittyson.schemas import Widget
from kittyson.weather import WeatherService

log = logging.getLogger("kittyson")
STATIC = Path(__file__).parent / "static"
MEOW = "🐱 kittyson v1"


def build_providers(settings: Settings, client: httpx.AsyncClient) -> list[Provider]:
    known: dict[str, Provider] = {
        "local": LocalProvider(settings.cats_inbox),
        "cataas": CataasProvider(client),
    }
    chosen: list[Provider] = []
    for key in settings.sources:
        if key in known:
            chosen.append(known[key])
        else:
            log.warning("unknown cat source %r ignored", key)
    return chosen


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    client = httpx.AsyncClient(headers={"User-Agent": f"kittyson/{__version__}"})
    app.state.settings = settings
    app.state.weather = WeatherService(client, settings.lat, settings.lon, settings.tz, settings.weather_ttl_seconds)
    app.state.cats = DailyCat(build_providers(settings, client), settings.cats_daily, settings.cat_size)
    settings.cats_inbox.mkdir(parents=True, exist_ok=True)
    settings.cats_daily.mkdir(parents=True, exist_ok=True)
    try:
        yield
    finally:
        await client.aclose()


app = FastAPI(title="kittyson", version=__version__, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/healthz")
async def healthz():
    return {"ok": True, "meow": "🐱"}


@app.get("/api/widget", response_model=Widget)
async def widget(request: Request):
    settings: Settings = request.app.state.settings
    now = clock.now(settings.tz)
    today = now.date()

    cat = await request.app.state.cats.get(today)
    weather_line = await request.app.state.weather.line()

    body = Widget(
        meow=MEOW,
        now=clock.iso_seconds(now),
        weekday=clock.weekday_ko(today),
        cat=cat.line if cat else "고양이 · missing",
        weather=weather_line,
        fortune=fortune_for(today),
    )
    return JSONResponse(body.model_dump(), headers={"Cache-Control": "no-store"})


@app.get("/cat/today.jpg", include_in_schema=False)
async def cat_today(request: Request):
    settings: Settings = request.app.state.settings
    cat = await request.app.state.cats.get(clock.today(settings.tz))
    if cat is None:
        return JSONResponse({"error": "no cat yet"}, status_code=503)
    return FileResponse(cat.path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=300"})


def run() -> None:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    uvicorn.run("kittyson.main:app", host=settings.host, port=settings.port, reload=False)
