import httpx

from kittyson.weather import Weather, WeatherService, parse

SAMPLE = {
    "current": {"temperature_2m": 11.4, "weather_code": 3, "is_day": 1},
    "daily": {"temperature_2m_max": [14.2], "temperature_2m_min": [5.6]},
}


def test_parse_and_line():
    w = parse(SAMPLE)
    assert w.line() == "☁️ 11° 흐림 ↑14 ↓6"


def test_night_clear_uses_moon():
    assert Weather(temp=3.2, high=9, low=1, code=0, is_day=False).line().startswith("🌙 3° 맑음")


def test_unknown_code_does_not_crash():
    assert "알 수 없음" in Weather(temp=0, high=0, low=0, code=123, is_day=True).line()


async def test_service_caches_and_keeps_last_good():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(200, json=SAMPLE)
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        svc = WeatherService(client, 37.5, 127.0, "Asia/Seoul", ttl=0)
        assert await svc.line() == "☁️ 11° 흐림 ↑14 ↓6"
        # ttl=0 forces a refetch; it fails, but the last good value survives
        assert await svc.line() == "☁️ 11° 흐림 ↑14 ↓6"
        assert calls["n"] == 2


async def test_service_without_any_data():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(503))) as client:
        svc = WeatherService(client, 37.5, 127.0, "Asia/Seoul", ttl=60)
        assert await svc.line() == "🐾 날씨 모름"
