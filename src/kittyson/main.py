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
from kittyson.deps import DailyCatDep, DailyQuoteDep, WeatherDep
from kittyson.schemas import Widget

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logs.configure()
    settings.cats_inbox.mkdir(parents=True, exist_ok=True)
    settings.cats_daily.mkdir(parents=True, exist_ok=True)
    settings.quotes.mkdir(parents=True, exist_ok=True)
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
async def widget(weather: WeatherDep, quote: DailyQuoteDep):
    now = clock.now(settings.tz)
    today = now.date()
    body = Widget(
        time=clock.time_str(now),
        date=clock.date_str(now),
        weekday=clock.weekday_ko(today),
        weather=await weather.line(),
        quote=quote.line(today),
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
    """Where today's cat came from, and the text colors that read well over the picture."""
    cat = await cats.get(clock.today(settings.tz))
    if cat is None:
        return JSONResponse({"error": "no cat yet"}, status_code=503)
    body = {"date": cat.day.isoformat(), "source": cat.source, "theme": cat.theme}
    return JSONResponse(body, headers={"Cache-Control": "public, max-age=300"})
