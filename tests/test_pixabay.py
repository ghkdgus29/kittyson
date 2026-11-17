import base64
import random
from datetime import date
from io import BytesIO

import httpx
import pytest
from claude_agent_sdk import ResultMessage
from PIL import Image

from kittyson import claude
from kittyson.cats import ClaudeChecker, PixabayProvider, check, pixabay
from kittyson.cats.check import described_as_cat
from tests.conftest import make_jpeg

DAY = date(2026, 11, 17)
KEY = "pixabay-key"


def photo(n: int, tags: str = "cat, pet, tabby") -> dict:
    return {"id": n, "tags": tags, "user": "누구", "largeImageURL": f"https://pixabay.com/get/{n}.jpg"}


def picture(n: int) -> bytes:
    return make_jpeg(color=(n, n, n))


class FakeChecker:
    """Says cat to every picture but the ones it is told are not."""

    def __init__(self, not_cats: tuple[int, ...] = (), error: Exception | None = None):
        self.not_cats = [picture(n) for n in not_cats]
        self.error = error
        self.looked = 0

    async def look(self, image: bytes) -> tuple[bool, str]:
        self.looked += 1
        if self.error:
            raise self.error
        return image not in self.not_cats, "사자"


def provider(photos: list[dict], checker: FakeChecker) -> tuple[PixabayProvider, list[httpx.Request]]:
    """A provider on a fake Pixabay: the search answers with `photos`, and photo n is picture(n)."""
    requests: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/":
            return httpx.Response(200, json={"totalHits": 500, "hits": photos})
        return httpx.Response(200, content=picture(int(request.url.path.split("/")[-1].removesuffix(".jpg"))))

    client = httpx.AsyncClient(transport=httpx.MockTransport(answer))
    return PixabayProvider(client, KEY, checker), requests


def downloaded(requests: list[httpx.Request]) -> list[str]:
    return [r.url.path for r in requests if r.url.path != "/api/"]


@pytest.mark.parametrize(
    ("text", "cat"),
    [
        ("A fluffy gray cat lounging on a warm, white blanket", True),
        ("Two kittens asleep in a basket", True),
        ("Close-up of a male lion stretching, showcasing its majestic mane", False),
        ("A big cat: a tiger resting in the grass", False),
        ("cat, kitten, pet", True),
        ("animal, tiger, big cat", False),
        ("Wooden bench in a park", False),
        ("A caterpillar on a leaf", False),  # 'cat' inside another word
        ("", False),
    ],
)
def test_a_description_names_a_cat_or_does_not(text: str, cat: bool):
    assert described_as_cat(text) is cat


async def test_searches_cat_photos_with_the_key():
    p, requests = provider([photo(1)], FakeChecker())
    assert await p.pick(DAY, random.Random(1)) == picture(1)

    search = requests[0]
    assert search.url.params["key"] == KEY
    assert search.url.params["q"] == "cat" and search.url.params["image_type"] == "photo"
    assert 1 <= int(search.url.params["page"]) <= pixabay.PAGES


async def test_a_photo_not_described_as_a_cat_is_not_downloaded():
    p, requests = provider([photo(1, "lion, big cat, mane"), photo(2), photo(3, "")], FakeChecker())
    assert await p.pick(DAY, random.Random(1)) == picture(2)
    assert downloaded(requests) == ["/get/2.jpg"]


async def test_when_claude_sees_no_cat_the_next_photo_is_tried():
    checker = FakeChecker(not_cats=(1, 2))
    p, requests = provider([photo(1), photo(2), photo(3)], checker)
    assert await p.pick(DAY, random.Random(1)) == picture(3)
    assert checker.looked == 3 and len(downloaded(requests)) == 3


async def test_gives_up_after_a_few_photos_that_are_not_cats():
    many = range(1, pixabay.TRIES + 3)
    checker = FakeChecker(not_cats=tuple(many))
    p, requests = provider([photo(n) for n in many], checker)
    with pytest.raises(LookupError):
        await p.pick(DAY, random.Random(1))
    assert checker.looked == pixabay.TRIES


async def test_a_refused_search_does_not_put_the_key_in_the_error():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(400, text="Invalid or missing API key")))
    with pytest.raises(RuntimeError) as failure:
        await PixabayProvider(client, KEY, FakeChecker()).pick(DAY, random.Random(1))
    assert "400" in str(failure.value) and KEY not in str(failure.value)


async def test_when_claude_cannot_look_the_tags_decide():
    p, _ = provider([photo(1)], FakeChecker(error=RuntimeError("Not logged in")))
    assert await p.pick(DAY, random.Random(1)) == picture(1)


async def test_claude_checker_shows_the_picture_and_reads_the_answer(monkeypatch: pytest.MonkeyPatch):
    seen = {}

    async def fake_query(*, prompt, options):
        seen["messages"] = [message async for message in prompt]
        seen["options"] = options
        yield ResultMessage(
            subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=2,
            session_id="s", total_cost_usd=0.001, structured_output={"cat": False, "what": "사자"},
        )

    monkeypatch.setattr(claude, "query", fake_query)
    assert await ClaudeChecker("haiku").look(make_jpeg(1200, 800)) == (False, "사자")

    image, text = seen["messages"][0]["message"]["content"]
    shown = Image.open(BytesIO(base64.b64decode(image["source"]["data"])))
    assert shown.size == (check.LOOK_SIZE, check.LOOK_SIZE)
    assert text["text"] == check.PROMPT
    assert seen["options"].tools == [] and seen["options"].model == "haiku"
