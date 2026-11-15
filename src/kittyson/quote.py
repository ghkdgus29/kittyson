"""One motivating line a day.

Claude writes the day's quote once (ClaudeWriter), told the date and the quotes of the last
two weeks so it does not repeat itself. DailyQuote keeps it in data/quotes/YYYY-MM-DD.json,
so the whole day shows the same quote.

Writing takes a few seconds, so it happens in the background. Until the quote is there, and
on days Claude cannot be reached (no token, no network), the day's pick from QUOTES shows.
"""

import asyncio
import json
import logging
import random
import time
from datetime import date
from pathlib import Path
from typing import Protocol

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from kittyson import clock

log = logging.getLogger(__name__)

QUOTES = [
    "오늘의 한 걸음이 내일의 길이 된다",
    "완벽보다 완료가 먼저다",
    "느려도 괜찮다, 멈추지만 않으면 된다",
    "작은 일을 끝내는 힘이 큰 일을 만든다",
    "미루고 싶은 그 일부터 시작하자",
    "실패는 방향을 알려 주는 표지판이다",
    "꾸준함은 재능을 이긴다",
    "오늘 심은 씨앗이 언젠가 그늘이 된다",
    "두려움은 해 보기 전이 가장 크다",
    "남이 아니라 어제의 나와 비교하자",
    "넘어진 자리가 다시 시작하는 자리다",
    "생각이 길어지면 용기는 줄어든다",
    "오 분만 해 보자, 그게 시작이다",
    "쉬어 가도 된다, 포기만 하지 말자",
    "잘하려 하지 말고 일단 하자",
    "기회는 준비된 사람에게 먼저 보인다",
    "어려운 길 끝에 좋은 경치가 있다",
    "한 번에 하나씩 하면 결국 다 된다",
    "지금이 가장 빠른 때다",
    "작은 성공이 모이면 자신감이 된다",
    "하기 싫은 날 해낸 것이 실력이 된다",
    "문제는 풀리라고 있는 것이다",
    "천천히 가는 사람이 멀리 간다",
    "오늘의 선택이 일 년 뒤의 나를 만든다",
    "버틴 하루는 반드시 힘이 된다",
    "끝까지 가 본 사람만 끝을 안다",
    "어제보다 한 뼘만 더 나아가자",
    "시작한 사람만이 고칠 수 있다",
    "땀 흘린 시간은 어디 가지 않는다",
    "할 수 있다고 믿으면 절반은 온 것이다",
]

ASK_CHARS = 28      # what Claude is asked to stay within
MAX_CHARS = 40      # what is accepted: three rows of the Large widget at most
RECENT_DAYS = 14    # quotes of this many past days are handed over as "do not repeat"
EXAMPLES = 6        # lines from QUOTES shown as the tone to keep
WRITE_TIMEOUT = 90  # seconds, CLI start included
RETRY_SECONDS = 30 * 60
MAX_TRIES = 3       # per day; after that the day keeps its line from QUOTES

SYSTEM = (
    "너는 kittyson 위젯에 매일 한 줄씩 올라가는 '오늘의 명언'을 쓰는 작가야. "
    "읽은 사람이 움직이고 싶어지는 문장을 담백하게 쓴다."
)

PROMPT = """오늘의 명언을 한 줄 써 줘.

오늘: {day} {weekday}

규칙
- 읽는 사람이 오늘 할 일을 시작하고 싶어지는, 동기를 북돋는 문장.
- 한국어 한 문장, 공백 포함 {ask}자 이내. 이모지, 따옴표, 줄바꿈은 쓰지 마.
- 네가 새로 쓴 문장이어야 해. 실제 인물의 말을 옮기거나 사람 이름을 붙이지 마.
- 뻔한 구호보다 그림이 떠오르는 문장이 좋아. 요일을 살짝 비춰도 좋아.
- 하루 종일 걸려 있는 문장이야. 아침, 저녁 같은 시간대는 넣지 마.
- 아래 '최근에 쓴 문장'과 문장도 소재도 겹치지 않게.

말투 예시
{examples}

최근에 쓴 문장
{recent}
"""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["quote"],
    "properties": {"quote": {"type": "string"}},
}


def quote_for(d: date) -> str:
    rng = random.Random(f"quote:{d.isoformat()}")
    return rng.choice(QUOTES)


class Writer(Protocol):
    async def write(self, day: date, recent: list[str]) -> str: ...


def _bullets(lines: list[str]) -> str:
    return "\n".join(f"- {line}" for line in lines)


def build_prompt(day: date, recent: list[str]) -> str:
    rng = random.Random(f"examples:{day.isoformat()}")
    return PROMPT.format(
        day=day.isoformat(),
        weekday=clock.weekday_ko(day),
        ask=ASK_CHARS,
        examples=_bullets(rng.sample(QUOTES, EXAMPLES)),
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

    async def write(self, day: date, recent: list[str]) -> str:
        options = ClaudeAgentOptions(
            tools=[],
            setting_sources=[],  # nothing from this machine's Claude settings leaks in
            system_prompt=SYSTEM,
            output_format={"type": "json_schema", "schema": SCHEMA},
            max_turns=3,  # the structured answer is a tool call, so one turn is not enough
            model=self._model,
        )
        result: ResultMessage | None = None
        async for message in query(prompt=build_prompt(day, recent), options=options):
            if isinstance(message, ResultMessage):
                result = message
        if result is None or result.is_error or not result.structured_output:
            detail = (result.errors or result.result) if result else "no result"
            raise RuntimeError(f"claude gave no quote: {detail}")
        log.info("quote written: turns=%s cost=%s", result.num_turns, result.total_cost_usd)
        return str(result.structured_output["quote"])


class DailyQuote:
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
            log.warning("unreadable quote %s: %s", path.name, exc)
            return None

    def recent(self, day: date) -> list[str]:
        """Quotes of the days before this one, newest first."""
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

    def line(self, day: date) -> str:
        """The day's quote, right away. Starts the writing when the day has none yet."""
        if hit := self.cached(day):
            return hit
        self._start(day)
        return quote_for(day)

    def _start(self, day: date) -> None:
        if self._task and not self._task.done():
            return
        if self._tried_day != day:
            self._tried_day, self._tries = day, 0
        elif self._tries >= self._max_tries or time.monotonic() - self._tried_at < self._retry_seconds:
            return
        self._tries += 1
        self._tried_at = time.monotonic()
        self._task = asyncio.create_task(self._write(day))

    async def _write(self, day: date) -> None:
        try:
            text = await asyncio.wait_for(self._writer.write(day, self.recent(day)), WRITE_TIMEOUT)
            line = clean(text)
        except Exception as exc:
            log.warning("quote for %s not written (try %s of %s): %s", day, self._tries, self._max_tries, exc)
            return
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._path(day)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"line": line, "source": "claude"}, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        log.info("quote of %s: %s", day, line)

    async def wait(self) -> None:
        """Wait for the writing in progress, if any. For tests and for a clean shutdown."""
        if self._task:
            await asyncio.gather(self._task, return_exceptions=True)

    async def close(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        await self.wait()
