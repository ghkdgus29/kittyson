"""Center-crop to a square and resize. Any provider's picture goes through here."""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


def square(data: bytes, size: int) -> Image.Image:
    img = Image.open(BytesIO(data))
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    return ImageOps.fit(img, (size, size), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def save_square(data: bytes, size: int, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    square(data, size).save(tmp, format="JPEG", quality=88, optimize=True)
    tmp.replace(dest)
