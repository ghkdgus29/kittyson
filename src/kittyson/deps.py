"""What the routes depend on, handed out through FastAPI's Depends.

Each object is built once and shared by every request: the weather service keeps its
last answer, the daily cat keeps the lock that stops two requests fetching at once, and
the daily quote keeps track of the line being written.
A route asks for one by type:

    async def widget(cats: DailyCatDep, weather: WeatherDep): ...

Tests swap them with app.dependency_overrides[get_daily_cat] = ...
"""

from functools import lru_cache
from typing import Annotated

import httpx
from fastapi import Depends

from kittyson import __version__
from kittyson.cats import CataasProvider, ClaudeChecker, DailyCat, LocalProvider, PixabayProvider, Provider
from kittyson.config import settings
from kittyson.quote import ClaudeWriter, DailyQuote
from kittyson.weather import WeatherService


@lru_cache
def get_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers={"User-Agent": f"kittyson/{__version__}"})


@lru_cache
def get_weather_service() -> WeatherService:
    return WeatherService(get_http_client(), settings.lat, settings.lon, settings.tz, settings.weather_ttl_seconds)


@lru_cache
def get_daily_cat() -> DailyCat:
    # Where cats come from. The day's seed picks one by weight (see each provider's default),
    # and the others follow in this order as fallbacks. To add or drop a source, edit this list.
    http = get_http_client()
    providers: list[Provider] = [
        LocalProvider(settings.cats_inbox),
        # Pixabay needs a key. Without one, cataas, which needs none.
        PixabayProvider(http, settings.pixabay_key, ClaudeChecker(settings.cat_model))
        if settings.pixabay_key
        else CataasProvider(http),
    ]
    return DailyCat(providers, settings.cats_daily, settings.cat_size)


@lru_cache
def get_daily_quote() -> DailyQuote:
    return DailyQuote(ClaudeWriter(settings.quote_model), settings.quotes)


WeatherDep = Annotated[WeatherService, Depends(get_weather_service)]
DailyCatDep = Annotated[DailyCat, Depends(get_daily_cat)]
DailyQuoteDep = Annotated[DailyQuote, Depends(get_daily_quote)]


def startup() -> None:
    """Build everything before the first request, so two early requests cannot build two."""
    get_weather_service()
    get_daily_cat()
    get_daily_quote()


async def shutdown() -> None:
    """Stop what is running and forget what was built. The next startup builds fresh ones."""
    await get_daily_quote().close()
    await get_http_client().aclose()
    for built in (get_daily_quote, get_daily_cat, get_weather_service, get_http_client):
        built.cache_clear()
