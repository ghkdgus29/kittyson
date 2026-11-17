"""pixabay.com: free with an API key, searched for cat photos.

A search can hand back something that is not a cat, and a photo that is not square loses
its sides. So a photo is checked twice before it is taken (check.py): its tags have to
name a cat, and then Claude looks at the square the widget would show. When that is not a
cat, the next photo is tried.
"""

import asyncio
import logging
import random
from datetime import date

import httpx

from kittyson.cats.check import Checker, described_as_cat

log = logging.getLogger(__name__)

URL = "https://pixabay.com/api/"
PER_PAGE = 100
PAGES = 5          # Pixabay hands out the 500 most popular photos of a search, no more
MIN_SIDE = 1024    # of the original, so the widget's square is not blown up
TRIES = 5          # photos downloaded and looked at before giving up for now
LOOK_TIMEOUT = 60  # seconds, CLI start included


class PixabayProvider:
    key = "pixabay"

    def __init__(self, client: httpx.AsyncClient, api_key: str, checker: Checker, weight: int = 1):
        self._client = client
        self._api_key = api_key
        self._checker = checker
        self._weight = weight

    def weight(self) -> int:
        return self._weight

    async def pick(self, day: date, rng: random.Random) -> bytes:
        params = {
            "key": self._api_key,
            "q": "cat",
            "image_type": "photo",
            "safesearch": "true",
            "min_width": MIN_SIDE,
            "min_height": MIN_SIDE,
            "per_page": PER_PAGE,
            "page": rng.randint(1, PAGES),
        }
        r = await self._client.get(URL, params=params, timeout=20)
        if r.status_code != 200:
            # Not raise_for_status(): its message has the URL in it, and the URL has the key.
            raise RuntimeError(f"pixabay search answered {r.status_code}: {r.text[:100]}")
        photos = [p for p in r.json()["hits"] if described_as_cat(p.get("tags") or "")]
        rng.shuffle(photos)

        for photo in photos[:TRIES]:
            r = await self._client.get(photo["largeImageURL"], timeout=20, follow_redirects=True)
            r.raise_for_status()
            if await self._is_cat(r.content, photo):
                log.info("pixabay photo %s by %s: %s", photo["id"], photo.get("user"), photo["tags"])
                return r.content
        raise LookupError(f"no cat among the {min(len(photos), TRIES)} pixabay photos tried")

    async def _is_cat(self, image: bytes, photo: dict) -> bool:
        try:
            cat, what = await asyncio.wait_for(self._checker.look(image), LOOK_TIMEOUT)
        except Exception as exc:
            # No token, no network: the tags said cat, and that has to do.
            log.warning("pixabay photo %s not looked at, going by its tags: %s", photo["id"], exc)
            return True
        if not cat:
            log.info("pixabay photo %s is not a cat (%s), trying another", photo["id"], what)
        return cat
