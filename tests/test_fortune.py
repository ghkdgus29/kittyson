import asyncio
import json
from datetime import date
from pathlib import Path

import pytest
from claude_agent_sdk import ResultMessage

from kittyson import fortune
from kittyson.fortune import FORTUNES, ClaudeWriter, DailyFortune, Hints, build_prompt, clean, fortune_for

DAY = date(2026, 11, 11)
HINTS = Hints(day=DAY, weekday="수요일", weather="☀️ 14° 맑음 ↑14 ↓4", cat="탱자 · snacky")


class FakeWriter:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls: list[tuple[Hints, list[str]]] = []

    async def write(self, hints: Hints, recent: list[str]) -> str:
        self.calls.append((hints, recent))
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def save(directory: Path, day: date, line: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{day.isoformat()}.json").write_text(json.dumps({"line": line}), encoding="utf-8")


def test_list_pick_is_stable_per_day():
    assert fortune_for(DAY) == fortune_for(DAY)
    assert fortune_for(DAY) in FORTUNES
    assert any(fortune_for(date(2026, 11, n)) != fortune_for(DAY) for n in range(12, 30))


def test_clean_keeps_a_plain_line_and_drops_wrapping_quotes():
    assert clean('  "햇볕 드는 자리는 내 거다"\n') == "햇볕 드는 자리는 내 거다"


@pytest.mark.parametrize("bad", ["", "   ", "첫 줄\n둘째 줄", '말 "속" 따옴표', "가" * (fortune.MAX_CHARS + 1)])
def test_clean_rejects_what_would_not_fit(bad: str):
    with pytest.raises(ValueError):
        clean(bad)


def test_every_list_line_passes_clean():
    assert all(clean(line) == line for line in FORTUNES)


def test_prompt_carries_the_day_and_the_recent_lines():
    prompt = build_prompt(HINTS, ["택배 상자는 나한테 온 것"])
    for part in ("2026-11-11 수요일", HINTS.weather, HINTS.cat, "- 택배 상자는 나한테 온 것"):
        assert part in prompt


async def test_first_request_shows_the_list_pick_then_the_written_line(tmp_path: Path):
    writer = FakeWriter("햇볕 드는 자리는 내 거다")
    daily = DailyFortune(writer, tmp_path)

    assert daily.line(HINTS) == fortune_for(DAY)  # nothing written yet, and nobody waits for it
    await daily.wait()
    assert daily.line(HINTS) == "햇볕 드는 자리는 내 거다"
    assert daily.line(HINTS) == "햇볕 드는 자리는 내 거다"
    assert len(writer.calls) == 1

    # A restart keeps the day's line.
    assert DailyFortune(FakeWriter(), tmp_path).line(HINTS) == "햇볕 드는 자리는 내 거다"


async def test_writer_is_told_the_lines_of_earlier_days_only(tmp_path: Path):
    save(tmp_path, date(2026, 11, 9), "그저께 문장")
    save(tmp_path, date(2026, 11, 10), "어제 문장")
    save(tmp_path, date(2026, 11, 12), "내일 문장")
    writer = FakeWriter("오늘 문장")
    daily = DailyFortune(writer, tmp_path)

    daily.line(HINTS)
    await daily.wait()
    assert writer.calls[0][1] == ["어제 문장", "그저께 문장"]


async def test_failure_keeps_the_list_pick_and_waits_before_retrying(tmp_path: Path):
    writer = FakeWriter(RuntimeError("no token"), "늦게 온 문장")
    daily = DailyFortune(writer, tmp_path, retry_seconds=3600)

    for _ in range(3):
        assert daily.line(HINTS) == fortune_for(DAY)
        await daily.wait()
    assert len(writer.calls) == 1


async def test_retries_stop_after_max_tries_and_start_again_the_next_day(tmp_path: Path):
    writer = FakeWriter(RuntimeError("down"), "가" * 40, "다음 날 문장")  # the second answer is too long
    daily = DailyFortune(writer, tmp_path, retry_seconds=0, max_tries=2)

    for _ in range(4):
        assert daily.line(HINTS) == fortune_for(DAY)
        await daily.wait()
    assert len(writer.calls) == 2
    assert not list(tmp_path.glob("*.json"))

    tomorrow = Hints(day=date(2026, 11, 12), weekday="목요일", weather=HINTS.weather, cat=HINTS.cat)
    daily.line(tomorrow)
    await daily.wait()
    assert daily.line(tomorrow) == "다음 날 문장"


async def test_close_cancels_a_writing_in_progress(tmp_path: Path):
    class SlowWriter:
        async def write(self, hints: Hints, recent: list[str]) -> str:
            await asyncio.sleep(60)
            return "끝내 못 쓴 문장"

    daily = DailyFortune(SlowWriter(), tmp_path)
    daily.line(HINTS)
    await daily.close()
    assert daily.cached(DAY) is None


def result(**over) -> ResultMessage:
    fields = dict(
        subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=2,
        session_id="s", total_cost_usd=0.001, structured_output={"fortune": "택배 상자는 나한테 온 것"},
    )
    return ResultMessage(**{**fields, **over})


async def test_claude_writer_reads_the_structured_answer(monkeypatch: pytest.MonkeyPatch):
    seen = {}

    async def fake_query(*, prompt, options):
        seen["prompt"], seen["options"] = prompt, options
        yield result()

    monkeypatch.setattr(fortune, "query", fake_query)
    assert await ClaudeWriter("haiku").write(HINTS, []) == "택배 상자는 나한테 온 것"
    assert HINTS.cat in seen["prompt"]
    assert seen["options"].tools == [] and seen["options"].model == "haiku"


async def test_claude_writer_raises_when_there_is_no_answer(monkeypatch: pytest.MonkeyPatch):
    async def fake_query(*, prompt, options):
        yield result(is_error=True, structured_output=None, result="Invalid API key")

    monkeypatch.setattr(fortune, "query", fake_query)
    with pytest.raises(RuntimeError, match="Invalid API key"):
        await ClaudeWriter("haiku").write(HINTS, [])
