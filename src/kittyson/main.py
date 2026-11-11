"""FastAPI app: the screen, the JSON, and today's cat.

Started the same way everywhere: `uvicorn kittyson.main:app` (see README and Dockerfile).
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from kittyson import __version__, clock, deps, logs
from kittyson.config import settings
from kittyson.deps import DailyCatDep, DailyFortuneDep, WeatherDep
from kittyson.fortune import Hints
from kittyson.schemas import Widget

STATIC = Path(__file__).parent / "static"
MEOW = "🐱 kittyson v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logs.configure()
    settings.cats_inbox.mkdir(parents=True, exist_ok=True)
    settings.cats_daily.mkdir(parents=True, exist_ok=True)
    settings.fortunes.mkdir(parents=True, exist_ok=True)
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


@app.get("/api/widget", response_model=Widget)
async def widget(cats: DailyCatDep, weather: WeatherDep, fortune: DailyFortuneDep):
    now = clock.now(settings.tz)
    today = now.date()

    cat = await cats.get(today)
    cat_line = cat.line if cat else "고양이 · missing"
    weather_line = await weather.line()
    weekday = clock.weekday_ko(today)

    body = Widget(
        meow=MEOW,
        time=clock.time_str(now),
        date=clock.date_str(now),
        weekday=weekday,
        cat=cat_line,
        weather=weather_line,
        fortune=fortune.line(Hints(day=today, weekday=weekday, weather=weather_line, cat=cat_line)),
    )
    return JSONResponse(body.model_dump(), headers={"Cache-Control": "no-store"})


@app.get("/cat/today.jpg", include_in_schema=False)
async def cat_today(cats: DailyCatDep):
    cat = await cats.get(clock.today(settings.tz))
    if cat is None:
        return JSONResponse({"error": "no cat yet"}, status_code=503)
    return FileResponse(cat.path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=300"})


@app.get("/cat/today.json")
async def cat_today_meta(cats: DailyCatDep):
    """Who today's cat is, and the text colors that read well over the picture."""
    cat = await cats.get(clock.today(settings.tz))
    if cat is None:
        return JSONResponse({"error": "no cat yet"}, status_code=503)
    body = {"date": cat.day.isoformat(), "name": cat.name, "mood": cat.mood, "source": cat.source, "theme": cat.theme}
    return JSONResponse(body, headers={"Cache-Control": "public, max-age=300"})
