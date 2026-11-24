"""FastAPI app: the screen, the JSON, and today's cat.

No request makes anything: the day's cat and quote are made ahead of the day (scheduler.py),
and a request reads what is there.

Started the same way everywhere: `uvicorn kittyson.main:app` (see README and Dockerfile).
"""

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from kittyson import __version__, clock, deps, logs
from kittyson.config import settings
from kittyson.deps import DailyCatDep, DailyQuoteDep, WeatherDep
from kittyson.quote import DailyQuote
from kittyson.schemas import Today, TodayCat, Widget
from kittyson.weather import WeatherService

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logs.configure()
    deps.startup()
    try:
        yield
    finally:
        await deps.shutdown()


app = FastAPI(title="kittyson", version=__version__, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/healthz")
async def healthz():
    return {"ok": True, "meow": "🐱"}


async def lines(now: datetime, weather: WeatherService, quotes: DailyQuote) -> Widget:
    quote = quotes.get(now.date())
    return Widget(
        time=clock.time_str(now),
        date=clock.date_str(now),
        weekday=clock.weekday_ko(now.date()),
        weather=await weather.line(),
        quote=quote.line,
        by=quote.by,
    )


@app.get("/api/today", response_model=Today)
async def today(weather: WeatherDep, cats: DailyCatDep, quotes: DailyQuoteDep):
    """All of today but the photo: the lines to draw, and the cat with its text colors."""
    now = clock.now(settings.tz)
    cat = cats.get(now.date())
    body = Today(
        widget=await lines(now, weather, quotes),
        cat=TodayCat(day=cat.day, source=cat.source, theme=cat.theme) if cat else None,
    )
    return JSONResponse(body.model_dump(mode="json"), headers={"Cache-Control": "no-store"})


@app.get("/cat/today.jpg", include_in_schema=False)
async def cat_today(cats: DailyCatDep):
    cat = cats.get(clock.today(settings.tz))
    if cat is None:
        return JSONResponse({"error": "no cat yet"}, status_code=503)
    return FileResponse(cats.photo(cat), media_type="image/jpeg", headers={"Cache-Control": "public, max-age=300"})
