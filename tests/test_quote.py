import asyncio
import json
from datetime import date
from pathlib import Path

import pytest
from claude_agent_sdk import ResultMessage

from kittyson import quote
from kittyson.quote import QUOTES, ClaudeWriter, DailyQuote, build_prompt, clean, quote_for

DAY = date(2026, 11, 11)
WRITTEN = "수요일의 반은 이미 내 편이다"
BY = "아무개"


class FakeWriter:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls: list[tuple[date, list[str]]] = []

    async def write(self, day: date, recent: list[str]) -> tuple[str, str]:
        self.calls.append((day, recent))
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer, BY


def save(directory: Path, day: date, line: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{day.isoformat()}.json").write_text(json.dumps({"line": line}), encoding="utf-8")


def test_list_pick_is_stable_per_day():
    assert quote_for(DAY) == quote_for(DAY)
    assert quote_for(DAY) in QUOTES
    assert any(quote_for(date(2026, 11, n)) != quote_for(DAY) for n in range(12, 30))


def test_clean_keeps_a_plain_line_and_drops_wrapping_quotes():
    assert clean(f'  "{WRITTEN}"\n') == WRITTEN


@pytest.mark.parametrize("bad", ["", "   ", "첫 줄\n둘째 줄", '말 "속" 따옴표', "가" * (quote.MAX_CHARS + 1)])
def test_clean_rejects_what_would_not_fit(bad: str):
    with pytest.raises(ValueError):
        clean(bad)


def test_every_list_line_passes_clean_and_is_as_short_as_claude_is_asked_to_be():
    assert all(clean(line) == line and len(line) <= quote.ASK_CHARS for line in QUOTES)


def test_prompt_carries_the_day_and_the_recent_lines_and_asks_for_a_real_quote():
    prompt = build_prompt(DAY, ["어제 나온 명언"])
    for part in ("2026-11-11 수요일", "- 어제 나온 명언", "실제 인물"):
        assert part in prompt
    assert any(f"오늘 찾아볼 곳: {field}\n" in prompt for field in quote.FIELDS)


async def test_first_request_shows_the_list_pick_then_the_written_line(tmp_path: Path):
    writer = FakeWriter(WRITTEN)
    daily = DailyQuote(writer, tmp_path)

    assert daily.line(DAY) == quote_for(DAY)  # nothing written yet, and nobody waits for it
    await daily.wait()
    assert daily.line(DAY) == WRITTEN
    assert daily.line(DAY) == WRITTEN
    assert len(writer.calls) == 1
    assert json.loads((tmp_path / "2026-11-11.json").read_text(encoding="utf-8"))["by"] == BY  # kept, not shown

    # A restart keeps the day's line.
    assert DailyQuote(FakeWriter(), tmp_path).line(DAY) == WRITTEN


async def test_writer_is_told_the_lines_of_earlier_days_only(tmp_path: Path):
    save(tmp_path, date(2026, 11, 9), "그저께 문장")
    save(tmp_path, date(2026, 11, 10), "어제 문장")
    save(tmp_path, date(2026, 11, 12), "내일 문장")
    writer = FakeWriter("오늘 문장")
    daily = DailyQuote(writer, tmp_path)

    daily.line(DAY)
    await daily.wait()
    assert writer.calls == [(DAY, ["어제 문장", "그저께 문장"])]


async def test_failure_keeps_the_list_pick_and_waits_before_retrying(tmp_path: Path):
    writer = FakeWriter(RuntimeError("no token"), "늦게 온 문장")
    daily = DailyQuote(writer, tmp_path, retry_seconds=3600)

    for _ in range(3):
        assert daily.line(DAY) == quote_for(DAY)
        await daily.wait()
    assert len(writer.calls) == 1


async def test_retries_stop_after_max_tries_and_start_again_the_next_day(tmp_path: Path):
    too_long = "가" * (quote.MAX_CHARS + 1)
    writer = FakeWriter(RuntimeError("down"), too_long, "다음 날 문장")
    daily = DailyQuote(writer, tmp_path, retry_seconds=0, max_tries=2)

    for _ in range(4):
        assert daily.line(DAY) == quote_for(DAY)
        await daily.wait()
    assert len(writer.calls) == 2
    assert not list(tmp_path.glob("*.json"))

    tomorrow = date(2026, 11, 12)
    daily.line(tomorrow)
    await daily.wait()
    assert daily.line(tomorrow) == "다음 날 문장"


async def test_close_cancels_a_writing_in_progress(tmp_path: Path):
    class SlowWriter:
        async def write(self, day: date, recent: list[str]) -> tuple[str, str]:
            await asyncio.sleep(60)
            return "끝내 못 고른 명언", BY

    daily = DailyQuote(SlowWriter(), tmp_path)
    daily.line(DAY)
    await daily.close()
    assert daily.cached(DAY) is None


def result(**over) -> ResultMessage:
    fields = dict(
        subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=2,
        session_id="s", total_cost_usd=0.001, structured_output={"quote": WRITTEN, "author": BY},
    )
    return ResultMessage(**{**fields, **over})


async def test_claude_writer_reads_the_structured_answer(monkeypatch: pytest.MonkeyPatch):
    seen = {}

    async def fake_query(*, prompt, options):
        seen["prompt"], seen["options"] = prompt, options
        yield result()

    monkeypatch.setattr(quote, "query", fake_query)
    assert await ClaudeWriter("haiku").write(DAY, []) == (WRITTEN, BY)
    assert "2026-11-11 수요일" in seen["prompt"]
    assert seen["options"].tools == [] and seen["options"].model == "haiku"


async def test_claude_writer_raises_when_there_is_no_answer(monkeypatch: pytest.MonkeyPatch):
    async def fake_query(*, prompt, options):
        yield result(is_error=True, structured_output=None, result="Invalid API key")

    monkeypatch.setattr(quote, "query", fake_query)
    with pytest.raises(RuntimeError, match="Invalid API key"):
        await ClaudeWriter("haiku").write(DAY, [])
