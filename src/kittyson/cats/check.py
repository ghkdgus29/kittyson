"""Is this picture a cat? Asked of pictures found by a search, where a lion can turn up.

Two checks: what the picture's description (or its tags) says, and what Claude sees in the picture.
"""

import asyncio
import base64
import re
from typing import Protocol

from kittyson.claude import ask
from kittyson.images import jpeg, square

CATS = {"cat", "cats", "kitten", "kittens", "kitty"}
BIG_CATS = {"lion", "lioness", "tiger", "leopard", "cheetah", "jaguar", "panther", "puma", "cougar", "lynx", "bobcat"}


def described_as_cat(text: str) -> bool:
    """English words that name a cat, and no big cat."""
    words = set(re.findall(r"[a-z]+", text.lower()))
    return bool(words & CATS) and not words & BIG_CATS


class Checker(Protocol):
    async def look(self, image: bytes) -> tuple[bool, str]:
        """Whether the picture is a cat, and what is in it."""
        ...


class ClaudeCatChecker:
    """Shows Claude the picture and asks."""

    LOOK_SIZE = 512  # what Claude is shown: the square the widget will show, smaller

    SYSTEM = "너는 kittyson 위젯의 배경으로 쓸 고양이 사진을 검사한다."
    PROMPT = (
        "이 사진의 주인공이 집고양이(다 큰 고양이나 새끼 고양이)인지 답해 줘. "
        "사자나 호랑이 같은 다른 동물이거나, 고양이가 없거나 거의 보이지 않으면 고양이가 아니다. "
        "what 에는 사진에 보이는 것을 한국어 몇 단어로 적는다."
    )
    SCHEMA = {
        "type": "object",
        "additionalProperties": False,
        "required": ["cat", "what"],
        "properties": {"cat": {"type": "boolean"}, "what": {"type": "string"}},
    }

    def __init__(self, model: str | None):
        self._model = model

    async def look(self, image: bytes) -> tuple[bool, str]:
        small = await asyncio.to_thread(self._shrink, image)  # decoding a photo is not for the event loop
        picture = {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(small).decode()}
        answer = await ask(
            [{"type": "image", "source": picture}, {"type": "text", "text": self.PROMPT}],
            system=self.SYSTEM,
            schema=self.SCHEMA,
            model=self._model,
        )
        return bool(answer["cat"]), str(answer.get("what", ""))

    def _shrink(self, image: bytes) -> bytes:
        return jpeg(square(image, self.LOOK_SIZE), quality=80)
