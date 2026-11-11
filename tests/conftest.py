from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image


def make_jpeg(w: int = 640, h: int = 480, color=(200, 120, 60)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def no_real_claude(monkeypatch: pytest.MonkeyPatch):
    """No test may reach Claude. A test that needs an answer puts its own fake query in."""

    def refuse(**kwargs):
        raise AssertionError("a test tried to call Claude")

    monkeypatch.setattr("kittyson.fortune.query", refuse)


@pytest.fixture
def jpeg_bytes() -> bytes:
    return make_jpeg()


@pytest.fixture
def inbox(tmp_path: Path) -> Path:
    d = tmp_path / "cats" / "inbox"
    d.mkdir(parents=True)
    return d
