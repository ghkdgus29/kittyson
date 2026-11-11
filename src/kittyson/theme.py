"""Text colors that stay readable over today's cat.

The JSON sits on the lower part of the photo, so only that area is measured.

- Light or dark text: whichever keeps more of the area readable. White text is scored
  against every cell of the area, black text too, and the better one wins.
- Accent lightness follows the area's median brightness, so keys and strings stay
  colorful on a dark photo and turn paler (or darker, for dark text) as it gets harder.
- Accent hues step away from the photo's dominant hue (no peach strings on a ginger cat).
- The halo behind the letters gets stronger when part of the area fights the text.

No scrim is drawn over the photo: the cat stays untouched, only the text adapts.
"""

import colorsys
import math
from pathlib import Path

from PIL import Image

VERSION = 1

TEXT_TOP = 0.32     # the JSON block covers the photo from this fraction of the height down
GRID = (48, 32)     # the text area is averaged into this many cells

KEY_HUES = (200, 165, 275)   # sky, mint, lavender. First one is the default.
STR_HUES = (32, 52, 335)     # peach, butter, pink
HUE_STRENGTH_MIN = 0.12      # below this the photo is too gray to have a dominant hue
HUE_TOO_CLOSE = 45           # degrees

CONTRAST_CAP = 7.0       # past this a cell is simply "readable"; more does not make up for bad cells
LIGHT_BIAS = 1.5         # dark text has to beat light text by this contrast factor
ACCENT_CONTRAST = 4.5    # keys and strings aim for this ratio against the median brightness

# What clients use before a theme is known. Same colors the screen started with.
DEFAULT = {
    "v": VERSION,
    "mode": "light",
    "punct": "#ffffff",
    "key": "#9cdcfe",
    "str": "#ffd9a8",
    "num": "#ffffff",
    "halo": "#000000",
    "halo_alpha": 0.9,
    "luma": [0.0, 0.0, 0.0],
}


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[float, float, float]) -> float:
    """WCAG relative luminance of an sRGB color given as 0..1 floats."""
    r, g, b = (_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def hex_luminance(color: str) -> float:
    return luminance(tuple(int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)))


def contrast(a: float, b: float) -> float:
    """WCAG contrast ratio between two luminances."""
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(_clamp(c, 0, 1) * 255):02x}" for c in rgb)


def _color(hue: float, target_luma: float, saturation: float) -> str:
    """The color of this hue whose luminance is target_luma (binary search on lightness)."""
    lo, hi = 0.0, 1.0
    for _ in range(24):
        mid = (lo + hi) / 2
        if luminance(colorsys.hls_to_rgb(hue / 360, mid, saturation)) < target_luma:
            lo = mid
        else:
            hi = mid
    return _hex(colorsys.hls_to_rgb(hue / 360, (lo + hi) / 2, saturation))


def _hue_distance(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _pick_hue(candidates: tuple[int, ...], dominant: float, strength: float) -> int:
    if strength < HUE_STRENGTH_MIN or _hue_distance(candidates[0], dominant) >= HUE_TOO_CLOSE:
        return candidates[0]
    return max(candidates, key=lambda h: _hue_distance(h, dominant))


def _percentile(pairs: list[tuple[float, float]], q: float) -> float:
    """Weighted percentile of (value, weight) pairs sorted by value."""
    total = sum(w for _, w in pairs)
    seen = 0.0
    for value, weight in pairs:
        seen += weight
        if seen >= total * q:
            return value
    return pairs[-1][0]


def _measure(img: Image.Image) -> tuple[list[tuple[float, float]], float, float]:
    """Luminance samples of the text area, plus its dominant hue (degrees) and how strong it is."""
    w, h = img.size
    area = img.convert("RGB").crop((0, round(h * TEXT_TOP), w, h)).resize(GRID, Image.Resampling.BOX)
    raw = area.tobytes()
    cols, rows = GRID

    samples: list[tuple[float, float]] = []
    hue_x = hue_y = weight_sum = 0.0
    for i in range(cols * rows):
        r, g, b = (raw[i * 3 + k] / 255 for k in range(3))
        # Lines are left-aligned, so the right edge is covered less often.
        x = (i % cols) / (cols - 1)
        weight = 1.0 if x <= 0.6 else 1.0 - (x - 0.6) * 1.5
        samples.append((luminance((r, g, b)), weight))

        hue, sat, val = colorsys.rgb_to_hsv(r, g, b)
        hue_x += math.cos(hue * math.tau) * sat * val * weight
        hue_y += math.sin(hue * math.tau) * sat * val * weight
        weight_sum += weight

    samples.sort()
    dominant = math.degrees(math.atan2(hue_y, hue_x)) % 360
    strength = math.hypot(hue_x, hue_y) / weight_sum
    return samples, dominant, strength


def _readability(samples: list[tuple[float, float]]) -> tuple[float, float]:
    """How well white text and black text read over the area (mean capped log contrast)."""
    light = dark = total = 0.0
    for luma, weight in samples:
        light += math.log(min(contrast(1.0, luma), CONTRAST_CAP)) * weight
        dark += math.log(min(contrast(0.0, luma), CONTRAST_CAP)) * weight
        total += weight
    return light / total, dark / total


def analyze(img: Image.Image) -> dict:
    samples, dominant, strength = _measure(img)
    p10, p50, p90 = (_percentile(samples, q) for q in (0.10, 0.50, 0.90))
    light_score, dark_score = _readability(samples)

    key_hue = _pick_hue(KEY_HUES, dominant, strength)
    str_hue = _pick_hue(STR_HUES, dominant, strength)

    if dark_score > light_score + math.log(LIGHT_BIAS):
        accent = _clamp((p50 + 0.05) / ACCENT_CONTRAST - 0.05, 0.02, 0.10)
        theme = {
            "mode": "dark",
            "punct": "#101010",
            "key": _color(key_hue, accent, 0.9),
            "str": _color(str_hue, accent, 0.9),
            "num": "#000000",
            "halo": "#ffffff",
            # Dark corners are where black letters get lost.
            "halo_alpha": round(_clamp(0.6 + (0.5 - p10) * 0.8, 0.6, 0.95), 2),
        }
    else:
        accent = _clamp((p50 + 0.05) * ACCENT_CONTRAST - 0.05, 0.58, 0.88)
        theme = {
            "mode": "light",
            "punct": "#ffffff",
            "key": _color(key_hue, accent, 0.95),
            "str": _color(str_hue, accent, 0.95),
            "num": "#ffffff",
            "halo": "#000000",
            # Bright patches are where white letters get lost.
            "halo_alpha": round(_clamp(0.6 + (p90 - 0.15) * 0.7, 0.6, 0.95), 2),
        }

    return {"v": VERSION, **theme, "luma": [round(p10, 3), round(p50, 3), round(p90, 3)]}


def for_file(path: Path) -> dict:
    with Image.open(path) as img:
        return analyze(img)
