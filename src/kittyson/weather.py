"""Open-Meteo current weather, cached for a while, with last-good fallback.

Produces a single short line such as: ☁️ 11° ↑14 ↓6 (now, today's high, today's low)
"""

import logging
import time
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)

API = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes -> (day emoji, night emoji).
# The emoji is all that is said about the sky: with words too, the line would not fit one widget row.
WMO: dict[int, tuple[str, str]] = {
    0: ("☀️", "🌙"),
    1: ("🌤️", "🌙"),
    2: ("⛅", "☁️"),
    3: ("☁️", "☁️"),
    45: ("🌫️", "🌫️"),
    48: ("🌫️", "🌫️"),
    51: ("🌦️", "🌧️"),
    53: ("🌦️", "🌧️"),
    55: ("🌧️", "🌧️"),
    56: ("🌧️", "🌧️"),
    57: ("🌧️", "🌧️"),
    61: ("🌦️", "🌧️"),
    63: ("🌧️", "🌧️"),
    65: ("🌧️", "🌧️"),
    66: ("🌧️", "🌧️"),
    67: ("🌧️", "🌧️"),
    71: ("🌨️", "🌨️"),
    73: ("🌨️", "🌨️"),
    75: ("❄️", "❄️"),
    77: ("🌨️", "🌨️"),
    80: ("🌦️", "🌧️"),
    81: ("🌧️", "🌧️"),
    82: ("🌧️", "🌧️"),
    85: ("🌨️", "🌨️"),
    86: ("❄️", "❄️"),
    95: ("⛈️", "⛈️"),
    96: ("⛈️", "⛈️"),
    99: ("⛈️", "⛈️"),
}


@dataclass(frozen=True)
class Weather:
    temp: float
    high: float
    low: float
    code: int
    is_day: bool

    def line(self) -> str:
        sky_day, sky_night = WMO.get(self.code, ("🐾", "🐾"))
        sky = sky_day if self.is_day else sky_night
        return f"{sky} {round(self.temp)}° ↑{round(self.high)} ↓{round(self.low)}"


def parse(payload: dict) -> Weather:
    cur = payload["current"]
    daily = payload["daily"]
    return Weather(
        temp=float(cur["temperature_2m"]),
        high=float(daily["temperature_2m_max"][0]),
        low=float(daily["temperature_2m_min"][0]),
        code=int(cur["weather_code"]),
        is_day=bool(cur.get("is_day", 1)),
    )


class WeatherService:
    def __init__(self, client: httpx.AsyncClient, lat: float, lon: float, tz: str, ttl: int):
        self._client = client
        self._params = {
            "latitude": lat,
            "longitude": lon,
            "timezone": tz,
            "current": "temperature_2m,weather_code,is_day",
            "daily": "temperature_2m_max,temperature_2m_min",
            "forecast_days": 1,
        }
        self._ttl = ttl
        self._cached: Weather | None = None
        self._fetched_at = 0.0

    async def current(self) -> Weather | None:
        if self._cached is not None and time.monotonic() - self._fetched_at < self._ttl:
            return self._cached
        try:
            r = await self._client.get(API, params=self._params, timeout=10)
            r.raise_for_status()
            self._cached = parse(r.json())
            self._fetched_at = time.monotonic()
        except Exception as exc:  # network, schema, anything: keep last good
            log.warning("weather fetch failed, keeping last value: %s", exc)
        return self._cached

    async def line(self) -> str:
        w = await self.current()
        return w.line() if w else "🐾 날씨 모름"
