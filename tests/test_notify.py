import json
import logging

import httpx
import pytest

from kittyson.notify import Telegram

TOKEN = "123456:secret-token"


async def test_telegram_sends_the_text_to_the_chat():
    requests: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    await Telegram(httpx.AsyncClient(transport=httpx.MockTransport(answer)), TOKEN, "42").send("고양이가 없어요")

    assert str(requests[0].url) == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    assert json.loads(requests[0].content) == {"chat_id": "42", "text": "고양이가 없어요"}


@pytest.mark.parametrize("failure", [httpx.ConnectError("no route"), httpx.Response(401, text="Unauthorized")])
async def test_a_message_that_cannot_be_sent_is_logged_without_the_token(failure, caplog: pytest.LogCaptureFixture):
    def answer(request: httpx.Request) -> httpx.Response:
        if isinstance(failure, Exception):
            raise failure
        return failure

    with caplog.at_level(logging.WARNING):
        await Telegram(httpx.AsyncClient(transport=httpx.MockTransport(answer)), TOKEN, "42").send("안녕")

    assert "telegram" in caplog.text and TOKEN not in caplog.text
