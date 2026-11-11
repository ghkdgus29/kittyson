from PIL import Image

from kittyson import theme


def flat(color) -> Image.Image:
    return Image.new("RGB", (200, 200), color)


def ratio(text_hex: str, background) -> float:
    return theme.contrast(theme.hex_luminance(text_hex), theme.luminance(tuple(c / 255 for c in background)))


def test_dark_photo_gets_light_text():
    t = theme.analyze(flat((20, 20, 24)))
    assert t["mode"] == "light"
    assert t["halo"] == "#000000"
    for key in ("punct", "key", "str", "num"):
        assert ratio(t[key], (20, 20, 24)) >= 7


def test_bright_photo_gets_dark_text():
    t = theme.analyze(flat((245, 245, 240)))
    assert t["mode"] == "dark"
    assert t["halo"] == "#ffffff"
    for key in ("punct", "key", "str", "num"):
        assert ratio(t[key], (245, 245, 240)) >= 4.5


def test_mid_tones_stay_readable():
    for gray in (60, 90, 120, 150, 180, 210):
        color = (gray, gray, gray)
        t = theme.analyze(flat(color))
        assert ratio(t["punct"], color) >= 3.5, gray
        assert ratio(t["key"], color) >= 3, gray
        assert ratio(t["str"], color) >= 3, gray


def test_only_the_text_area_counts():
    # White ceiling, dark floor: the JSON sits on the floor.
    img = flat((250, 250, 250))
    img.paste((15, 15, 15), (0, 60, 200, 200))
    assert theme.analyze(img)["mode"] == "light"


def test_accents_avoid_the_photo_hue():
    plain = theme.analyze(flat((20, 20, 20)))
    blue = theme.analyze(flat((10, 40, 90)))
    assert plain["key"] != blue["key"]  # a blue photo pushes keys off sky blue
    assert plain["str"] == blue["str"]  # peach strings were never close to blue


def test_bright_patches_strengthen_the_halo():
    dark = flat((15, 15, 15))
    patchy = flat((15, 15, 15))
    patchy.paste((255, 255, 255), (0, 120, 60, 200))
    assert theme.analyze(patchy)["mode"] == "light"
    assert theme.analyze(patchy)["halo_alpha"] > theme.analyze(dark)["halo_alpha"]
