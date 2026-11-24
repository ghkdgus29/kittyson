from datetime import date
from io import BytesIO

import pytest
from PIL import Image

from kittyson.cats import Photo
from kittyson.config import settings
from kittyson.quote import Quote


def make_jpeg(w: int = 640, h: int = 480, color=(200, 120, 60)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def nothing_real(monkeypatch: pytest.MonkeyPatch):
    """No test may reach Claude, Pixabay or Telegram, whatever this machine's .env holds.
    A test that needs an answer puts its own fake in."""

    def refuse(**kwargs):
        raise AssertionError("a test tried to call Claude")

    monkeypatch.setattr("kittyson.claude.query", refuse)
    monkeypatch.setattr(settings, "pixabay_key", "")
    monkeypatch.setattr(settings, "telegram_token", "")
    monkeypatch.setattr(settings, "telegram_chat", "")


@pytest.fixture
def jpeg_bytes() -> bytes:
    return make_jpeg()


class FakeSource:
    """Hands out the photos it was given, one a call. An exception in their place is raised.
    Given none, it has a new photo every time."""

    key = "fake"

    def __init__(self, *answers: Photo | Exception):
        self.answers = list(answers)
        self.endless = not answers
        self.seen: list[set[str]] = []  # what each call was told not to pick

    async def pick(self, seen: set[str]) -> Photo:
        self.seen.append(set(seen))
        if self.endless:
            return Photo(id=str(len(self.seen)), data=make_jpeg())
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


class FakeWriter:
    """Writes the quotes it was given, one a call. An exception in their place is raised.
    Given none, it writes the same quote every time."""

    LINE = "수요일의 반은 이미 내 편이다"
    BY = "아무개"

    def __init__(self, *answers: str | Exception):
        self.answers = list(answers)
        self.endless = not answers
        self.calls: list[tuple[date, list[Quote]]] = []

    async def write(self, day: date, recent: list[Quote]) -> tuple[str, str]:
        self.calls.append((day, recent))
        answer = self.LINE if self.endless else self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer, self.BY
