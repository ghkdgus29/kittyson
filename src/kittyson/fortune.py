"""One line a day.

Claude writes the day's line once (ClaudeWriter), told the date, the weather, today's cat
and the lines of the last two weeks so it does not repeat itself. DailyFortune keeps it in
data/fortunes/YYYY-MM-DD.json, so the whole day shows the same line.

Writing takes a few seconds, so it happens in the background. Until the line is there, and
on days Claude cannot be reached (no token, no network), the day's pick from FORTUNES shows.
"""

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

log = logging.getLogger(__name__)

FORTUNES = [
    "낮잠은 생산성이다",
    "오늘은 일단 누워보자",
    "츄르는 답을 알고 있다",
    "햇빛 드는 자리를 먼저 차지할 것",
    "급할수록 천천히, 고양이처럼",
    "상자가 있으면 들어가야 한다",
    "오늘의 목표: 아무것도 안 하기",
    "그루밍은 자기관리다",
    "창밖을 보는 것도 일이다",
    "밥 먹고 자고, 또 먹고 자기",
    "꾹꾹이는 사랑이다",
    "모르는 건 일단 냄새부터 맡자",
    "키보드 위가 제일 따뜻하다",
    "오늘은 새벽 4시에 우다다",
    "쓰다듬는 손은 거절하지 않는다",
    "궁금하면 일단 쳐서 떨어뜨리기",
    "하루 열여섯 시간의 수면은 기본",
    "오늘은 창틀에서 보내는 날",
    "울지 말고 야옹 해",
    "모든 봉지는 열어볼 가치가 있다",
    "작은 틈도 내 자리가 된다",
    "꼬리로 말해도 다 알아들어",
    "물그릇 옆에서 물 달라고 하기",
    "배를 보여줘도 만지지 마",
    "오늘의 사냥감: 양말 한 짝",
    "따뜻한 노트북은 좋은 침대",
    "밤에는 복도를 전력 질주",
    "오늘은 액체처럼 살기",
    "눈 천천히 깜빡이면 사랑해",
    "일단 앉아. 그다음 생각해",
]

ASK_CHARS = 18      # what Claude is asked to stay within
MAX_CHARS = 22      # what is accepted: two rows of the Large widget at most
RECENT_DAYS = 14    # lines of this many past days are handed over as "do not repeat"
EXAMPLES = 6        # lines from FORTUNES shown as the tone to keep
WRITE_TIMEOUT = 90  # seconds, CLI start included
RETRY_SECONDS = 30 * 60
MAX_TRIES = 3       # per day; after that the day keeps its line from FORTUNES

SYSTEM = (
    "너는 kittyson 위젯에 매일 한 줄씩 올라가는 '고양이의 한 마디'를 쓰는 작가야. "
    "고양이 눈으로 본 느긋하고 엉뚱한 생활 지침을 담백한 반말로 쓴다."
)

PROMPT = """오늘의 한 마디를 한 줄 써 줘.

오늘: {day} {weekday}
날씨: {weather}
오늘의 고양이: {cat}

규칙
- 한국어 한 줄, 공백 포함 {ask}자 이내. 이모지, 따옴표, 줄바꿈은 쓰지 마.
- 날씨, 요일, 고양이의 기분 중 하나를 살짝 비춰도 좋아. 기온 숫자나 고양이 이름을 그대로 넣지는 마.
- 아래 '최근에 쓴 문장'과 문장도 소재도 겹치지 않게.

말투 예시
{examples}

최근에 쓴 문장
{recent}
"""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["fortune"],
    "properties": {"fortune": {"type": "string"}},
}


def fortune_for(d: date) -> str:
    rng = random.Random(f"fortune:{d.isoformat()}")
    return rng.choice(FORTUNES)


@dataclass(frozen=True)
class Hints:
    """What the day is like. The line may lean on it."""

    day: date
    weekday: str
    weather: str
    cat: str


class Writer(Protocol):
    async def write(self, hints: Hints, recent: list[str]) -> str: ...


def _bullets(lines: list[str]) -> str:
    return "\n".join(f"- {line}" for line in lines)


def build_prompt(hints: Hints, recent: list[str]) -> str:
    rng = random.Random(f"examples:{hints.day.isoformat()}")
    return PROMPT.format(
        day=hints.day.isoformat(),
        weekday=hints.weekday,
        weather=hints.weather,
        cat=hints.cat,
        ask=ASK_CHARS,
        examples=_bullets(rng.sample(FORTUNES, EXAMPLES)),
        recent=_bullets(recent) if recent else "- (아직 없음)",
    )


def clean(text: str) -> str:
    """The line as it goes into the JSON, or ValueError when it would not sit well in the widget."""
    line = text.strip().strip("\"'“”‘’").strip()
    if not line:
        raise ValueError("empty line")
    if "\n" in line or '"' in line:
        raise ValueError(f"not a plain single line: {line!r}")
    if len(line) > MAX_CHARS:
        raise ValueError(f"{len(line)} characters, over {MAX_CHARS}: {line!r}")
    return line


class ClaudeWriter:
    """Asks Claude through the Claude Agent SDK: no tools, one structured answer.

    Signs in the way the claude CLI does: CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY in the
    environment, or a logged-in claude on this machine.
    """

    def __init__(self, model: str | None):
        self._model = model

    async def write(self, hints: Hints, recent: list[str]) -> str:
        options = ClaudeAgentOptions(
            tools=[],
            setting_sources=[],  # nothing from this machine's Claude settings leaks in
            system_prompt=SYSTEM,
            output_format={"type": "json_schema", "schema": SCHEMA},
            max_turns=3,  # the structured answer is a tool call, so one turn is not enough
            model=self._model,
        )
        result: ResultMessage | None = None
        async for message in query(prompt=build_prompt(hints, recent), options=options):
            if isinstance(message, ResultMessage):
                result = message
        if result is None or result.is_error or not result.structured_output:
            detail = (result.errors or result.result) if result else "no result"
            raise RuntimeError(f"claude gave no fortune: {detail}")
        log.info("fortune written: turns=%s cost=%s", result.num_turns, result.total_cost_usd)
        return str(result.structured_output["fortune"])


class DailyFortune:
    def __init__(
        self,
        writer: Writer,
        directory: Path,
        retry_seconds: float = RETRY_SECONDS,
        max_tries: int = MAX_TRIES,
    ):
        self._writer = writer
        self._dir = directory
        self._retry_seconds = retry_seconds
        self._max_tries = max_tries
        self._task: asyncio.Task | None = None
        self._tried_day: date | None = None
        self._tries = 0
        self._tried_at = 0.0

    def _path(self, day: date) -> Path:
        return self._dir / f"{day.isoformat()}.json"

    def cached(self, day: date) -> str | None:
        path = self._path(day)
        if not path.exists():
            return None
        try:
            return clean(json.loads(path.read_text(encoding="utf-8"))["line"])
        except (ValueError, KeyError, TypeError) as exc:
            log.warning("unreadable fortune %s: %s", path.name, exc)
            return None

    def recent(self, day: date) -> list[str]:
        """Lines of the days before this one, newest first."""
        if not self._dir.exists():
            return []
        lines: list[str] = []
        for path in sorted(self._dir.glob("*.json"), reverse=True):
            try:
                past = date.fromisoformat(path.stem)
            except ValueError:
                continue
            if past < day and (line := self.cached(past)):
                lines.append(line)
            if len(lines) == RECENT_DAYS:
                break
        return lines

    def line(self, hints: Hints) -> str:
        """The day's line, right away. Starts the writing when the day has none yet."""
        if hit := self.cached(hints.day):
            return hit
        self._start(hints)
        return fortune_for(hints.day)

    def _start(self, hints: Hints) -> None:
        if self._task and not self._task.done():
            return
        if self._tried_day != hints.day:
            self._tried_day, self._tries = hints.day, 0
        elif self._tries >= self._max_tries or time.monotonic() - self._tried_at < self._retry_seconds:
            return
        self._tries += 1
        self._tried_at = time.monotonic()
        self._task = asyncio.create_task(self._write(hints))

    async def _write(self, hints: Hints) -> None:
        try:
            text = await asyncio.wait_for(self._writer.write(hints, self.recent(hints.day)), WRITE_TIMEOUT)
            line = clean(text)
        except Exception as exc:
            log.warning("fortune for %s not written (try %s of %s): %s", hints.day, self._tries, self._max_tries, exc)
            return
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._path(hints.day)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"line": line, "source": "claude"}, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        log.info("fortune of %s: %s", hints.day, line)

    async def wait(self) -> None:
        """Wait for the writing in progress, if any. For tests and for a clean shutdown."""
        if self._task:
            await asyncio.gather(self._task, return_exceptions=True)

    async def close(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        await self.wait()
