import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from claude_agent_sdk import ResultMessage

from kittyson import claude
from kittyson.quote import QUOTES, ClaudeQuoteWriter, DailyQuote, Quote, fallback
from kittyson.store import DayStore
from tests.conftest import FakeWriter

DAY = date(2026, 11, 11)
WRITTEN = FakeWriter.LINE
BY = FakeWriter.BY


def daily(directory: Path, writer: FakeWriter) -> DailyQuote:
    return DailyQuote(writer, DayStore(directory, Quote))


def quote(day: date, line: str, by: str = BY) -> Quote:
    return Quote(day=day, line=line, by=by)


def test_a_quote_keeps_a_plain_line_and_drops_wrapping_quotes():
    q = Quote(day=DAY, line=f'  "{WRITTEN}"\n', by=f" {BY} ")
    assert (q.line, q.by) == (WRITTEN, BY)


@pytest.mark.parametrize("bad", ["", "   ", "첫 줄\n둘째 줄", '말 "속" 따옴표', "가" * (Quote.LIMITS["line"] + 1)])
def test_a_line_that_would_not_sit_well_is_refused(bad: str):
    with pytest.raises(ValueError):
        Quote(day=DAY, line=bad, by=BY)


@pytest.mark.parametrize("bad", ["", "니체, 우상의 황혼 (1889년)", "이름\n둘째 줄"])
def test_a_name_that_is_not_just_a_short_name_is_refused(bad: str):
    with pytest.raises(ValueError):
        Quote(day=DAY, line=WRITTEN, by=bad)


def test_every_quote_of_the_list_is_a_quote_and_none_comes_twice():
    for line, by in QUOTES:
        q = Quote(day=DAY, line=line, by=by)
        assert (q.line, q.by) == (line, by)
    assert len({line for line, _ in QUOTES}) == len(QUOTES)


def test_the_list_gives_each_day_its_quote_one_after_another():
    assert fallback(DAY) == fallback(DAY)
    days = [DAY + timedelta(days=n) for n in range(len(QUOTES))]
    assert {fallback(day).line for day in days} == {line for line, _ in QUOTES}  # no repeat until the list is through


def test_prompt_carries_the_day_and_the_recent_quotes_and_asks_for_a_whole_motivating_quote():
    writer = ClaudeQuoteWriter("haiku")
    prompt = writer.prompt(DAY, [quote(date(2026, 11, 10), "어제 나온 명언", "어제 사람")])
    for part in ("2026-11-11 수요일", "- 어제 나온 명언 (어제 사람)", "실제 인물", "동기부여", "명언 전체"):
        assert part in prompt
    assert f"{ClaudeQuoteWriter.ASK_CHARS}자 이내" in prompt
    assert ClaudeQuoteWriter.ASK_CHARS <= Quote.LIMITS["line"]


def test_where_claude_looks_follows_from_the_day():
    writer = ClaudeQuoteWriter("haiku")
    assert writer.prompt(DAY, []) == writer.prompt(DAY, [])
    fields = [
        next(f for f in ClaudeQuoteWriter.FIELDS if f"오늘 찾아볼 곳: {f}\n" in writer.prompt(DAY + timedelta(days=n), []))
        for n in range(len(ClaudeQuoteWriter.FIELDS))
    ]
    assert sorted(fields) == sorted(ClaudeQuoteWriter.FIELDS)  # each in its turn


async def test_a_day_shows_the_list_quote_until_its_own_is_made(tmp_path: Path):
    writer = FakeWriter(WRITTEN)
    quotes = daily(tmp_path, writer)
    assert quotes.get(DAY) == fallback(DAY)  # reading makes nothing
    assert writer.calls == []

    await quotes.make(DAY)
    await quotes.make(DAY)
    assert quotes.get(DAY) == quote(DAY, WRITTEN)
    assert len(writer.calls) == 1
    assert json.loads((tmp_path / "2026-11-11.json").read_text(encoding="utf-8"))["by"] == BY

    # A restart keeps the day's quote.
    assert daily(tmp_path, FakeWriter()).get(DAY) == quote(DAY, WRITTEN)


async def test_writer_is_told_the_quotes_of_earlier_days_only_newest_first(tmp_path: Path):
    store = DayStore(tmp_path, Quote)
    for day, line in ((9, "그저께 문장"), (10, "어제 문장"), (12, "내일 문장")):
        store.save(quote(date(2026, 11, day), line))
    writer = FakeWriter("오늘 문장")

    await daily(tmp_path, writer).make(DAY)
    assert writer.calls == [(DAY, [quote(date(2026, 11, 10), "어제 문장"), quote(date(2026, 11, 9), "그저께 문장")])]


async def test_a_quote_that_cannot_be_written_or_does_not_fit_is_not_saved(tmp_path: Path):
    too_long = "가" * (Quote.LIMITS["line"] + 1)
    quotes = daily(tmp_path, FakeWriter(RuntimeError("no token"), too_long, "세 번째에 온 문장"))

    with pytest.raises(RuntimeError):
        await quotes.make(DAY)
    with pytest.raises(ValueError):
        await quotes.make(DAY)
    assert not list(tmp_path.glob("*")) and quotes.get(DAY) == fallback(DAY)

    await quotes.make(DAY)
    assert quotes.get(DAY).line == "세 번째에 온 문장"


def test_quotes_saved_by_the_first_version_are_still_read(tmp_path: Path):
    old = {"line": "시련은 있어도 실패는 없다", "by": "정주영", "source": "claude"}
    (tmp_path / "2026-11-11.json").write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
    assert daily(tmp_path, FakeWriter()).get(DAY) == quote(DAY, "시련은 있어도 실패는 없다", "정주영")


def result(**over) -> ResultMessage:
    fields = dict(
        subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=2,
        session_id="s", total_cost_usd=0.001, structured_output={"quote": WRITTEN, "author": BY},
    )
    return ResultMessage(**{**fields, **over})


async def test_claude_quote_writer_reads_the_structured_answer(monkeypatch: pytest.MonkeyPatch):
    seen = {}

    async def fake_query(*, prompt, options):
        seen["prompt"], seen["options"] = prompt, options
        yield result()

    monkeypatch.setattr(claude, "query", fake_query)
    assert await ClaudeQuoteWriter("haiku").write(DAY, []) == (WRITTEN, BY)
    assert "2026-11-11 수요일" in seen["prompt"]
    assert seen["options"].system_prompt == ClaudeQuoteWriter.SYSTEM
    assert seen["options"].tools == [] and seen["options"].model == "haiku"


async def test_claude_quote_writer_raises_when_there_is_no_answer(monkeypatch: pytest.MonkeyPatch):
    async def fake_query(*, prompt, options):
        yield result(is_error=True, structured_output=None, result="Invalid API key")

    monkeypatch.setattr(claude, "query", fake_query)
    with pytest.raises(RuntimeError, match="Invalid API key"):
        await ClaudeQuoteWriter("haiku").write(DAY, [])
