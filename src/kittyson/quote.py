"""One motivating line a day, said by a real person.

Claude picks the day's quote once (ClaudeWriter), told the date and the quotes of the last
two months so it does not repeat itself. DailyQuote keeps it in data/quotes/YYYY-MM-DD.json
with who said it, so the whole day shows the same quote. Only the line is shown.

Picking takes a few seconds, so it happens in the background. Until the quote is there, and
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

from kittyson import clock
from kittyson.claude import ask

log = logging.getLogger(__name__)

# Each with who said it and where, so it can be looked up.
QUOTES = [
    "천 리 길도 한 걸음부터 시작된다",  # 노자, 도덕경 64장
    "배우고 때때로 익히면 또한 기쁘지 아니한가",  # 공자, 논어 학이편
    "멈추지 않고 새기면 쇠와 돌에도 새길 수 있다",  # 순자, 권학편
    "신에게는 아직 열두 척의 배가 있습니다",  # 이순신, 1597년 (이분, 이충무공 행록)
    "하루라도 책을 읽지 않으면 입안에 가시가 돋는다",  # 안중근, 뤼순 감옥에서 쓴 글씨
    "시련은 있어도 실패는 없다",  # 정주영, 1991년 자서전 제목
    "시작한 사람은 이미 절반을 해낸 것이다",  # 호라티우스, 서간시 1권 2
    "오늘을 붙잡아라",  # 호라티우스, 송가 1권 11
    "운명은 용감한 자를 돕는다",  # 베르길리우스, 아이네이스 10권
    "할 수 있다고 믿기에 할 수 있다",  # 베르길리우스, 아이네이스 5권
    "떨어지는 물방울이 돌을 뚫는다",  # 오비디우스, 흑해에서 온 편지 4권 10
    "삶이 있는 한 희망은 있다",  # 키케로, 아티쿠스에게 보낸 편지 9권 10
    "길을 막는 것이 곧 길이 된다",  # 마르쿠스 아우렐리우스, 명상록 5권 20
    "인간은 노력하는 한 방황한다",  # 괴테, 파우스트
    "나를 죽이지 못하는 것은 나를 더 강하게 만든다",  # 니체, 우상의 황혼
    "나는 내 운명의 주인, 내 영혼의 선장이다",  # 윌리엄 어니스트 헨리, 시 인빅터스
    "노력하고, 구하고, 찾고, 굴복하지 않으리",  # 테니슨, 시 율리시스
    "자기 자신을 믿어라",  # 에머슨, 자기 신뢰
    "오늘 할 수 있는 일을 내일로 미루지 마라",  # 벤저민 프랭클린, 부자가 되는 길 (1758)
    "우연은 준비된 사람만 돕는다",  # 파스퇴르, 1854년 릴 과학대학 개교 연설
    "위대한 일은 작은 일들이 모여 이루어진다",  # 반 고흐, 1882년 10월 22일 테오에게 보낸 편지
    "천재는 1%의 영감과 99%의 노력이다",  # 에디슨, 1932년 하퍼스 먼슬리에 실린 말
    "상상력은 지식보다 중요하다",  # 아인슈타인, 1929년 새터데이 이브닝 포스트 인터뷰
    "나는 날마다 모든 면에서 점점 더 좋아지고 있다",  # 에밀 쿠에, 자기암시
    "우리가 두려워할 것은 두려움 그 자체뿐이다",  # 프랭클린 루스벨트, 1933년 취임 연설
    "결코 굴복하지 마라. 결코, 결코, 결코",  # 처칠, 1941년 해로 스쿨 연설
    "쉬워서가 아니라 어렵기 때문에 한다",  # 케네디, 1962년 라이스 대학 연설
    "나에게는 꿈이 있습니다",  # 마틴 루서 킹, 1963년 워싱턴 행진 연설
    "인간은 파괴될 수는 있어도 패배하지는 않는다",  # 헤밍웨이, 노인과 바다
    "다시 시도하라. 다시 실패하라. 더 낫게 실패하라",  # 사뮈엘 베케트, 최악을 향하여
]

# Where Claude looks on a given day, so the days differ in more than the sentence.
FIELDS = ["철학자", "과학자", "작가나 시인", "예술가", "운동선수", "기업가", "정치가나 지도자", "동양 고전", "한국 인물"]

ASK_CHARS = 28      # what Claude is asked to stay within
MAX_CHARS = 40      # what is accepted: three rows of the Large widget at most
RECENT_DAYS = 60    # quotes of this many past days are handed over as "do not repeat"
WRITE_TIMEOUT = 90  # seconds, CLI start included
RETRY_SECONDS = 30 * 60
MAX_TRIES = 3       # per day; after that the day keeps its line from QUOTES

SYSTEM = (
    "너는 kittyson 위젯에 매일 한 줄씩 올라가는 '오늘의 명언'을 고르는 편집자야. "
    "실제 인물이 실제로 남긴 말만, 알려진 그대로 옮긴다."
)

PROMPT = """오늘의 명언을 하나 골라 줘.

오늘: {day} {weekday}
오늘 찾아볼 곳: {field}

규칙
- 실제 인물이 실제로 남긴, 읽는 사람이 오늘 할 일을 시작하고 싶어지는 명언.
- 책, 연설, 편지, 인터뷰처럼 출처가 분명한 말만 고른다. 지어내지 마.
- 누가 했는지 확실하지 않은 말, 다른 사람의 말로 잘못 알려진 말, 속담은 고르지 않는다.
- 한국어로, 널리 쓰이는 번역 그대로. 공백 포함 {ask}자 이내인 명언을 고르고, 길이를 맞추려고 줄이거나 바꾸지 않는다.
- quote 에는 문장만 넣는다. 이름, 이모지, 따옴표, 줄바꿈은 넣지 않는다. 말한 사람은 author 에 적는다.
- 아래 '최근에 나온 명언'과 겹치지 않게.

최근에 나온 명언
{recent}
"""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["quote", "author"],
    "properties": {"quote": {"type": "string"}, "author": {"type": "string"}},
}


def quote_for(d: date) -> str:
    rng = random.Random(f"quote:{d.isoformat()}")
    return rng.choice(QUOTES)


class Writer(Protocol):
    async def write(self, day: date, recent: list[str]) -> tuple[str, str]:
        """The quote and who said it."""


def _bullets(lines: list[str]) -> str:
    return "\n".join(f"- {line}" for line in lines)


def build_prompt(day: date, recent: list[str]) -> str:
    rng = random.Random(f"field:{day.isoformat()}")
    return PROMPT.format(
        day=day.isoformat(),
        weekday=clock.weekday_ko(day),
        field=rng.choice(FIELDS),
        ask=ASK_CHARS,
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
    def __init__(self, model: str | None):
        self._model = model

    async def write(self, day: date, recent: list[str]) -> tuple[str, str]:
        answer = await ask(build_prompt(day, recent), system=SYSTEM, schema=SCHEMA, model=self._model)
        return str(answer["quote"]), str(answer.get("author", ""))


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
            text, by = await asyncio.wait_for(self._writer.write(day, self.recent(day)), WRITE_TIMEOUT)
            line = clean(text)
        except Exception as exc:
            log.warning("quote for %s not written (try %s of %s): %s", day, self._tries, self._max_tries, exc)
            return
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._path(day)
        tmp = path.with_suffix(".tmp")
        record = {"line": line, "by": by, "source": "claude"}
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        log.info("quote of %s: %s (%s)", day, line, by)

    async def wait(self) -> None:
        """Wait for the writing in progress, if any. For tests and for a clean shutdown."""
        if self._task:
            await asyncio.gather(self._task, return_exceptions=True)

    async def close(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        await self.wait()
