"""cataas.com: free, no key, one random cat per request."""

import random
from datetime import date

import httpx

from kittyson.cats.base import CatPick

URL = "https://cataas.com/cat"


class CataasProvider:
    key = "cataas"

    def __init__(self, client: httpx.AsyncClient, weight: int = 1):
        self._client = client
        self._weight = weight

    def weight(self) -> int:
        return self._weight

    async def pick(self, day: date, rng: random.Random) -> CatPick:
        r = await self._client.get(URL, params={"type": "square"}, timeout=20, follow_redirects=True)
        r.raise_for_status()
        if not r.headers.get("content-type", "").startswith("image/"):
            raise ValueError(f"cataas returned {r.headers.get('content-type')}")
        return CatPick(image=r.content)
