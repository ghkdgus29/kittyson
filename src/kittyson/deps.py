"""What the app is made of, built once and shared.

A route asks for what it needs by type, through FastAPI's Depends:

    async def today(weather: WeatherDep, cats: DailyCatDep, quotes: DailyQuoteDep): ...

The scheduler is given the same daily cat and daily quote, so what it makes is what the
routes read.

Tests put fakes in place of what reaches the outside: cat_source, quote_writer and notifier
(monkeypatch on this module), and the weather (app.dependency_overrides).
"""

from functools import lru_cache
from typing import Annotated

import httpx
from fastapi import Depends

from kittyson import __version__
from kittyson.cats import CatStore, ClaudeCatChecker, DailyCat, Pixabay, Source
from kittyson.config import settings
from kittyson.notify import Notifier, Telegram
from kittyson.quote import ClaudeQuoteWriter, DailyQuote, Quote, QuoteWriter
from kittyson.scheduler import Scheduler
from kittyson.store import DayStore
from kittyson.weather import WeatherService


@lru_cache
def get_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers={"User-Agent": f"kittyson/{__version__}"})


def cat_source() -> Source:
    return Pixabay(get_http_client(), settings.pixabay_key, ClaudeCatChecker(settings.cat_model))


def quote_writer() -> QuoteWriter:
    return ClaudeQuoteWriter(settings.quote_model)


def notifier() -> Notifier | None:
    if settings.telegram_token and settings.telegram_chat:
        return Telegram(get_http_client(), settings.telegram_token, settings.telegram_chat)
    return None


@lru_cache
def get_weather_service() -> WeatherService:
    return WeatherService(get_http_client(), settings.lat, settings.lon, settings.tz, settings.weather_ttl_seconds)


@lru_cache
def get_daily_cat() -> DailyCat:
    return DailyCat(cat_source(), CatStore(settings.cats_daily), settings.cat_size)


@lru_cache
def get_daily_quote() -> DailyQuote:
    return DailyQuote(quote_writer(), DayStore(settings.quotes, Quote))


@lru_cache
def get_scheduler() -> Scheduler:
    return Scheduler([get_daily_cat(), get_daily_quote()], notifier(), settings.tz)


WeatherDep = Annotated[WeatherService, Depends(get_weather_service)]
DailyCatDep = Annotated[DailyCat, Depends(get_daily_cat)]
DailyQuoteDep = Annotated[DailyQuote, Depends(get_daily_quote)]


def startup() -> None:
    """Build everything before the first request, and start making the days."""
    get_weather_service()
    get_scheduler().start()


async def shutdown() -> None:
    """Stop what is running and forget what was built. The next startup builds fresh ones."""
    await get_scheduler().stop()
    await get_http_client().aclose()
    for built in (get_scheduler, get_daily_quote, get_daily_cat, get_weather_service, get_http_client):
        built.cache_clear()
