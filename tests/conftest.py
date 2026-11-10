from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image


def make_jpeg(w: int = 640, h: int = 480, color=(200, 120, 60)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def jpeg_bytes() -> bytes:
    return make_jpeg()


@pytest.fixture
def inbox(tmp_path: Path) -> Path:
    d = tmp_path / "cats" / "inbox"
    d.mkdir(parents=True)
    return d
