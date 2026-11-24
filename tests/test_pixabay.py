import base64
from io import BytesIO

import httpx
import pytest
from claude_agent_sdk import ResultMessage
from PIL import Image

from kittyson import claude
from kittyson.cats import ClaudeCatChecker, Pixabay
from kittyson.cats.check import described_as_cat
from tests.conftest import make_jpeg

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


def source(
    popular: list[dict], checker: FakeChecker, latest: list[dict] | None = None
) -> tuple[Pixabay, list[httpx.Request]]:
    """A source on a fake Pixabay: the search answers with `popular` or `latest`, a page at a
    time, and photo n is picture(n)."""
    requests: list[httpx.Request] = []
    found = {"popular": popular, "latest": latest or []}

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/":
            params = request.url.params
            start = (int(params["page"]) - 1) * int(params["per_page"])
            hits = found[params["order"]][start : start + int(params["per_page"])]
            return httpx.Response(200, json={"totalHits": 500, "hits": hits})
        return httpx.Response(200, content=picture(int(request.url.path.split("/")[-1].removesuffix(".jpg"))))

    client = httpx.AsyncClient(transport=httpx.MockTransport(answer))
    return Pixabay(client, KEY, checker), requests


def searched(requests: list[httpx.Request]) -> list[tuple[str, str]]:
    return [(r.url.params["order"], r.url.params["page"]) for r in requests if r.url.path == "/api/"]


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


async def test_searches_the_most_popular_cat_photos_with_the_key():
    p, requests = source([photo(1)], FakeChecker())
    found = await p.pick(set())
    assert (found.id, found.data, found.skipped) == ("1", picture(1), ())

    search = requests[0].url.params
    assert search["key"] == KEY
    assert search["q"] == "cat" and search["image_type"] == "photo"
    assert (search["order"], search["page"]) == ("popular", "1")


async def test_takes_the_first_photo_not_used_yet_so_the_same_past_gives_the_same_photo():
    photos = [photo(n) for n in (1, 2, 3, 4)]
    for _ in range(3):
        p, requests = source(photos, FakeChecker())
        assert (await p.pick({"1", "2"})).id == "3"
        assert downloaded(requests) == ["/get/3.jpg"]


async def test_a_photo_not_described_as_a_cat_is_not_downloaded():
    p, requests = source([photo(1, "lion, big cat, mane"), photo(2), photo(3, "")], FakeChecker())
    assert (await p.pick(set())).id == "2"
    assert downloaded(requests) == ["/get/2.jpg"]


async def test_when_claude_sees_no_cat_the_next_photo_is_tried_and_the_skipped_ones_are_handed_over():
    checker = FakeChecker(not_cats=(1, 2))
    p, requests = source([photo(1), photo(2), photo(3)], checker)
    found = await p.pick(set())
    assert (found.id, found.skipped) == ("3", ("1", "2"))
    assert checker.looked == 3 and len(downloaded(requests)) == 3


async def test_gives_up_after_a_few_photos_that_are_not_cats_and_a_retry_goes_on_past_them():
    not_cats = tuple(range(1, Pixabay.TRIES + 2))
    checker = FakeChecker(not_cats=not_cats)
    p, requests = source([photo(n) for n in (*not_cats, 100)], checker)
    with pytest.raises(LookupError):
        await p.pick(set())
    assert checker.looked == Pixabay.TRIES

    found = await p.pick(set())
    assert found.id == "100" and found.skipped == tuple(str(n) for n in not_cats)
    assert checker.looked == len(not_cats) + 1  # none was looked at twice


async def test_goes_on_to_the_next_page_and_then_to_the_newest_photos(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(Pixabay, "PER_PAGE", 2)
    popular = [photo(n) for n in (1, 2, 3, 4, 5)]
    p, requests = source(popular, FakeChecker(), latest=[photo(5), photo(6)])

    assert (await p.pick({"1", "2"})).id == "3"
    assert searched(requests) == [("popular", "1"), ("popular", "2")]

    requests.clear()
    assert (await p.pick({"1", "2", "3", "4", "5"})).id == "6"
    assert searched(requests) == [("popular", "1"), ("popular", "2"), ("popular", "3"), ("latest", "1")]


async def test_when_every_photo_is_used_there_is_no_cat():
    p, _ = source([photo(1), photo(2)], FakeChecker(), latest=[photo(2)])
    with pytest.raises(LookupError):
        await p.pick({"1", "2"})


async def test_a_refused_search_does_not_put_the_key_in_the_error():
    refuse = httpx.MockTransport(lambda request: httpx.Response(400, text="Invalid or missing API key"))
    with pytest.raises(RuntimeError) as failure:
        await Pixabay(httpx.AsyncClient(transport=refuse), KEY, FakeChecker()).pick(set())
    assert "400" in str(failure.value) and KEY not in str(failure.value)


async def test_without_a_key_nothing_is_asked():
    def no_request(request: httpx.Request) -> httpx.Response:
        raise AssertionError("asked without a key")

    with pytest.raises(RuntimeError, match="KITTYSON_PIXABAY_KEY"):
        await Pixabay(httpx.AsyncClient(transport=httpx.MockTransport(no_request)), "", FakeChecker()).pick(set())


async def test_when_claude_cannot_look_the_tags_decide():
    p, _ = source([photo(1)], FakeChecker(error=RuntimeError("Not logged in")))
    assert (await p.pick(set())).id == "1"


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
    assert await ClaudeCatChecker("haiku").look(make_jpeg(1200, 800)) == (False, "사자")

    image, text = seen["messages"][0]["message"]["content"]
    shown = Image.open(BytesIO(base64.b64decode(image["source"]["data"])))
    assert shown.size == (ClaudeCatChecker.LOOK_SIZE, ClaudeCatChecker.LOOK_SIZE)
    assert text["text"] == ClaudeCatChecker.PROMPT
    assert seen["options"].tools == [] and seen["options"].model == "haiku"
