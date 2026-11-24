"""A message to the person who runs the server, for when something needs their eyes."""

import logging
from typing import Protocol

import httpx

log = logging.getLogger(__name__)


class Notifier(Protocol):
    async def send(self, text: str) -> None:
        """Never raises: a message that cannot be sent is logged, no more."""
        ...


class Telegram:
    """Through a Telegram bot (made with @BotFather), to one chat."""

    URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, client: httpx.AsyncClient, token: str, chat: str):
        self._client = client
        self._token = token
        self._chat = chat

    async def send(self, text: str) -> None:
        try:
            r = await self._client.post(
                self.URL.format(token=self._token), json={"chat_id": self._chat, "text": text}, timeout=10
            )
        except httpx.HTTPError as exc:
            # Only the kind of error: its message can have the URL in it, and the URL has the token.
            log.warning("telegram not reached: %s", type(exc).__name__)
            return
        if r.status_code != 200:
            log.warning("telegram answered %s: %s", r.status_code, r.text[:200])
