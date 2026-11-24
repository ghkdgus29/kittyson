"""pixabay.com: free with an API key, searched for cat photos.

The search answers in a fixed order (the most popular first), and the first photo not used
yet is taken. Nothing is left to chance: which photo a day gets follows from the photos the
days before it got.

A search can hand back something that is not a cat, and a photo that is not square loses
its sides. So a photo is checked twice before it is taken (check.py): its tags have to
name a cat, and then Claude looks at the square the widget would show. When that is not a
cat, the photo is skipped for good and the next one is tried.
"""

import asyncio
import logging
from collections.abc import AsyncIterator

import httpx

from kittyson.cats.check import Checker, described_as_cat
from kittyson.cats.daily import Photo

log = logging.getLogger(__name__)


class Pixabay:
    key = "pixabay"

    URL = "https://pixabay.com/api/"
    ORDERS = ("popular", "latest")  # the popular photos first. When those are used up, the newest
    PER_PAGE = 100
    PAGES = 5          # Pixabay hands out the first 500 photos of a search, no more
    MIN_SIDE = 1024    # of the original, so the widget's square is not blown up
    TRIES = 5          # photos downloaded and looked at before giving up for now
    LOOK_TIMEOUT = 60  # seconds, CLI start included

    def __init__(self, client: httpx.AsyncClient, api_key: str, checker: Checker):
        self._client = client
        self._api_key = api_key
        self._checker = checker
        # Photos found not to be cats. They are saved with the next cat that is found
        # (Photo.skipped); until then they are remembered here, so a retry goes on past them.
        self._not_cats: list[str] = []

    async def pick(self, seen: set[str]) -> Photo:
        if not self._api_key:
            raise RuntimeError("no Pixabay key (KITTYSON_PIXABAY_KEY)")
        tried = 0
        async for hit in self._search():
            id = str(hit["id"])
            if id in seen or id in self._not_cats or not described_as_cat(hit.get("tags") or ""):
                continue
            if tried == self.TRIES:
                break
            tried += 1
            r = await self._client.get(hit["largeImageURL"], timeout=20, follow_redirects=True)
            r.raise_for_status()
            if await self._is_cat(r.content, id):
                log.info("pixabay photo %s by %s: %s", id, hit.get("user"), hit["tags"])
                skipped, self._not_cats = tuple(self._not_cats), []
                return Photo(id=id, data=r.content, skipped=skipped)
            self._not_cats.append(id)
        raise LookupError(f"no new cat among the {tried} pixabay photos tried")

    async def _search(self) -> AsyncIterator[dict]:
        """Every photo the search hands out, in its order. Pages are asked for as they are needed."""
        for order in self.ORDERS:
            for page in range(1, self.PAGES + 1):
                params = {
                    "key": self._api_key,
                    "q": "cat",
                    "image_type": "photo",
                    "safesearch": "true",
                    "min_width": self.MIN_SIDE,
                    "min_height": self.MIN_SIDE,
                    "order": order,
                    "per_page": self.PER_PAGE,
                    "page": page,
                }
                r = await self._client.get(self.URL, params=params, timeout=20)
                if r.status_code != 200:
                    # Not raise_for_status(): its message has the URL in it, and the URL has the key.
                    raise RuntimeError(f"pixabay search answered {r.status_code}: {r.text[:100]}")
                hits = r.json()["hits"]
                for hit in hits:
                    yield hit
                if len(hits) < self.PER_PAGE:  # the last page
                    break

    async def _is_cat(self, image: bytes, id: str) -> bool:
        try:
            cat, what = await asyncio.wait_for(self._checker.look(image), self.LOOK_TIMEOUT)
        except Exception as exc:
            # No token, no network: the tags said cat, and that has to do.
            log.warning("pixabay photo %s not looked at, going by its tags: %s", id, exc)
            return True
        if not cat:
            log.info("pixabay photo %s is not a cat (%s), trying another", id, what)
        return cat
