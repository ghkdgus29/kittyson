"""Open-Meteo current weather, cached for a while, with last-good fallback.

Produces a single line such as: ☁️ 11° 흐림 ↑14 ↓6
"""

import logging
import time
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)

API = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes -> (day emoji, night emoji, Korean description)
WMO: dict[int, tuple[str, str, str]] = {
    0: ("☀️", "🌙", "맑음"),
    1: ("🌤️", "🌙", "대체로 맑음"),
    2: ("⛅", "☁️", "구름 조금"),
    3: ("☁️", "☁️", "흐림"),
    45: ("🌫️", "🌫️", "안개"),
    48: ("🌫️", "🌫️", "서리 안개"),
    51: ("🌦️", "🌧️", "약한 이슬비"),
    53: ("🌦️", "🌧️", "이슬비"),
    55: ("🌧️", "🌧️", "강한 이슬비"),
    56: ("🌧️", "🌧️", "언 이슬비"),
    57: ("🌧️", "🌧️", "언 이슬비"),
    61: ("🌦️", "🌧️", "약한 비"),
    63: ("🌧️", "🌧️", "비"),
    65: ("🌧️", "🌧️", "강한 비"),
    66: ("🌧️", "🌧️", "언 비"),
    67: ("🌧️", "🌧️", "언 비"),
    71: ("🌨️", "🌨️", "약한 눈"),
    73: ("🌨️", "🌨️", "눈"),
    75: ("❄️", "❄️", "강한 눈"),
    77: ("🌨️", "🌨️", "싸락눈"),
    80: ("🌦️", "🌧️", "소나기"),
    81: ("🌧️", "🌧️", "소나기"),
    82: ("🌧️", "🌧️", "강한 소나기"),
    85: ("🌨️", "🌨️", "소낙눈"),
    86: ("❄️", "❄️", "강한 소낙눈"),
    95: ("⛈️", "⛈️", "뇌우"),
    96: ("⛈️", "⛈️", "우박 뇌우"),
    99: ("⛈️", "⛈️", "강한 우박 뇌우"),
}


@dataclass(frozen=True)
class Weather:
    temp: float
    high: float
    low: float
    code: int
    is_day: bool

    def line(self) -> str:
        sky_day, sky_night, desc = WMO.get(self.code, ("🐾", "🐾", "알 수 없음"))
        sky = sky_day if self.is_day else sky_night
        return f"{sky} {round(self.temp)}° {desc} ↑{round(self.high)} ↓{round(self.low)}"


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
