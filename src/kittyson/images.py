"""Center-crop to a square and resize. Every cat photo goes through here."""

from io import BytesIO

from PIL import Image, ImageOps


def square(data: bytes, size: int) -> Image.Image:
    img = Image.open(BytesIO(data))
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    return ImageOps.fit(img, (size, size), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def jpeg(img: Image.Image, quality: int = 88) -> bytes:
    out = BytesIO()
    img.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()
