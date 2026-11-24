"""One motivating quote a day, with who said it.

Claude picks the day's quote (ClaudeQuoteWriter), told the date and the quotes of the last
two months so it does not repeat itself. It is made once, ahead of the day (scheduler.py),
and kept in data/quotes/YYYY-MM-DD.json. On a day without one (no token, no network) the
day's quote from QUOTES shows.
"""

import logging
from datetime import date
from typing import ClassVar, Protocol

from pydantic import ValidationInfo, field_validator

from kittyson import clock
from kittyson.claude import ask
from kittyson.store import DayRecord, DayStore

log = logging.getLogger(__name__)


class Quote(DayRecord):
    """A whole quote and the name of who said it, each short enough to sit well on the watch."""

    # Characters. On the 46 mm watch a quote this long takes three rows and a name this long one,
    # with the letters still at about 15 pt (17 pt for a quote of up to 27). A longer quote runs onto a fourth row, a longer name onto a second.
    LIMITS: ClassVar[dict[str, int]] = {"line": 36, "by": 9}

    line: str
    by: str

    @field_validator("line", "by")
    @classmethod
    def _plain_and_short(cls, text: str, info: ValidationInfo) -> str:
        text = text.strip().strip("\"'“”‘’").strip()
        limit = cls.LIMITS[info.field_name]
        if not text or "\n" in text or '"' in text:
            raise ValueError(f"not a plain single line: {text!r}")
        if len(text) > limit:
            raise ValueError(f"{len(text)} characters, over {limit}: {text!r}")
        return text


# For the days Claude wrote nothing. Each with where it was said, so it can be looked up.
QUOTES = [
    ("천 리 길도 한 걸음부터 시작된다", "노자"),  # 도덕경 64장
    ("멈추지 않고 새기면 쇠와 돌에도 새길 수 있다", "순자"),  # 권학편
    ("배우고 때때로 익히면 또한 기쁘지 아니한가", "공자"),  # 논어 학이편
    ("신에게는 아직 열두 척의 배가 있습니다", "이순신"),  # 1597년 (이분, 이충무공 행록)
    ("하루라도 책을 읽지 않으면 입안에 가시가 돋는다", "안중근"),  # 뤼순 감옥에서 쓴 글씨
    ("시련은 있어도 실패는 없다", "정주영"),  # 1991년 자서전 제목
    ("시작한 사람은 이미 절반을 해낸 것이다", "호라티우스"),  # 서간시 1권 2
    ("오늘을 붙잡아라", "호라티우스"),  # 송가 1권 11
    ("운명은 용감한 자를 돕는다", "베르길리우스"),  # 아이네이스 10권
    ("할 수 있다고 믿기에 할 수 있다", "베르길리우스"),  # 아이네이스 5권
    ("떨어지는 물방울이 돌을 뚫는다", "오비디우스"),  # 흑해에서 온 편지 4권 10
    ("삶이 있는 한 희망은 있다", "키케로"),  # 아티쿠스에게 보낸 편지 9권 10
    ("길을 막는 것이 곧 길이 된다", "아우렐리우스"),  # 명상록 5권 20
    ("인간은 노력하는 한 방황한다", "괴테"),  # 파우스트
    ("나를 죽이지 못하는 것은 나를 더 강하게 만든다", "니체"),  # 우상의 황혼
    ("나는 내 운명의 주인, 내 영혼의 선장이다", "W. E. 헨리"),  # 윌리엄 어니스트 헨리의 시 인빅터스
    ("노력하고, 구하고, 찾고, 굴복하지 않으리", "테니슨"),  # 시 율리시스
    ("자기 자신을 믿어라", "에머슨"),  # 자기 신뢰
    ("오늘 할 수 있는 일을 내일로 미루지 마라", "벤저민 프랭클린"),  # 부자가 되는 길 (1758)
    ("고통 없이는 얻는 것도 없다", "벤저민 프랭클린"),  # 부자가 되는 길 (1758)
    ("나는 폭풍이 두렵지 않다. 내 배를 모는 법을 배우고 있으니까", "루이자 메이 올컷"),  # 작은 아씨들
    ("우연은 준비된 사람만 돕는다", "파스퇴르"),  # 1854년 릴 과학대학 개교 연설
    ("위대한 일은 작은 일들이 모여 이루어진다", "반 고흐"),  # 1882년 10월 22일 테오에게 보낸 편지
    ("천재는 1%의 영감과 99%의 노력이다", "에디슨"),  # 1932년 하퍼스 먼슬리에 실린 말
    ("나는 날마다 모든 면에서 점점 더 좋아지고 있다", "에밀 쿠에"),  # 자기암시
    ("우리가 두려워할 것은 두려움 그 자체뿐이다", "프랭클린 루스벨트"),  # 1933년 취임 연설
    ("인생은 과감한 모험이거나, 아무것도 아니다", "헬렌 켈러"),  # Let Us Have Faith (1940)
    ("결코 굴복하지 마라. 결코, 결코, 결코", "처칠"),  # 1941년 해로 스쿨 연설
    ("쉬워서가 아니라 어렵기 때문에 한다", "케네디"),  # 1962년 라이스 대학 연설
    ("인간은 파괴될 수는 있어도 패배하지는 않는다", "헤밍웨이"),  # 노인과 바다
    ("다시 시도하라. 다시 실패하라. 더 낫게 실패하라", "사뮈엘 베케트"),  # 최악을 향하여
    ("끝날 때까지 끝난 게 아니다", "요기 베라"),  # 1973년 뉴욕 메츠 감독 시절
    ("시도하지 않은 슛은 100% 빗나간다", "웨인 그레츠키"),  # 1983년 하키 뉴스 인터뷰
    ("나는 살면서 수없이 실패했다. 그것이 내가 성공한 이유다", "마이클 조던"),  # 1997년 나이키 광고
]


def fallback(day: date) -> Quote:
    """The day's quote from QUOTES: one after another, a day each."""
    line, by = QUOTES[day.toordinal() % len(QUOTES)]
    return Quote(day=day, line=line, by=by)


class QuoteWriter(Protocol):
    async def write(self, day: date, recent: list[Quote]) -> tuple[str, str]:
        """The quote and who said it. `recent`: the quotes of the days before, not to be repeated."""
        ...


class ClaudeQuoteWriter:
    """Asks Claude for the day's quote."""

    # Where Claude looks on a given day, so the days differ in more than the sentence.
    FIELDS = ("철학자", "과학자", "작가나 시인", "예술가", "운동선수", "기업가", "정치가나 지도자", "동양 고전", "한국 인물")
    ASK_CHARS = 32  # what Claude is asked to keep the quote within. Quote accepts a little more: Claude counts roughly

    SYSTEM = (
        "너는 kittyson 위젯에 매일 하나씩 올라가는 '오늘의 명언'을 고르는 편집자야. "
        "실제 인물이 실제로 남긴 말만, 알려진 그대로 옮긴다."
    )
    PROMPT = """오늘의 명언을 하나 골라 줘.

오늘: {day} {weekday}
오늘 찾아볼 곳: {field}

규칙
- 읽는 사람이 오늘 할 일을 바로 시작하고 싶어지는 동기부여 명언. 도전, 끈기, 용기, 실행에 대한 말이 좋다.
- 실제 인물이 책, 연설, 편지, 인터뷰처럼 출처가 분명한 곳에 남긴 말만 고른다. 지어내지 마.
- 누가 했는지 확실하지 않은 말, 다른 사람의 말로 잘못 알려진 말, 속담은 고르지 않는다.
- 한국어로, 널리 쓰이는 번역 그대로.
- 명언 전체를 옮긴다. 긴 말의 일부만 떼어 내거나, 길이를 맞추려고 줄이거나 바꾸지 않는다. 처음부터 전체가 공백 포함 {ask}자 이내인 명언을 고른다.
- quote 에는 문장만 넣는다. 이름, 이모지, 따옴표, 줄바꿈은 넣지 않는다.
- author 에는 말한 사람의 이름만, 한국에서 흔히 부르는 짧은 이름으로 공백 포함 {by}자 이내로 적는다(예: 니체, 아우렐리우스, 스티브 잡스). 직함, 출처, 연도는 넣지 않는다.
- 아래 '최근에 나온 명언'과 겹치지 않게, 같은 사람이 자주 나오지 않게.

최근에 나온 명언
{recent}
"""
    SCHEMA = {
        "type": "object",
        "additionalProperties": False,
        "required": ["quote", "author"],
        "properties": {"quote": {"type": "string"}, "author": {"type": "string"}},
    }

    def __init__(self, model: str | None):
        self._model = model

    def prompt(self, day: date, recent: list[Quote]) -> str:
        return self.PROMPT.format(
            day=day.isoformat(),
            weekday=clock.weekday_ko(day),
            field=self.FIELDS[day.toordinal() % len(self.FIELDS)],
            ask=self.ASK_CHARS,
            by=Quote.LIMITS["by"],
            recent="\n".join(f"- {quote.line} ({quote.by})" for quote in recent) or "- (아직 없음)",
        )

    async def write(self, day: date, recent: list[Quote]) -> tuple[str, str]:
        answer = await ask(self.prompt(day, recent), system=self.SYSTEM, schema=self.SCHEMA, model=self._model)
        return str(answer["quote"]), str(answer["author"])


class DailyQuote:
    name = "명언"

    RECENT_DAYS = 60  # quotes of this many past days are handed over as "do not repeat"

    def __init__(self, writer: QuoteWriter, store: DayStore[Quote]):
        self._writer = writer
        self._store = store

    def get(self, day: date) -> Quote:
        """The day's quote. While none is written, the one from QUOTES."""
        return self._store.load(day) or fallback(day)

    async def make(self, day: date) -> None:
        """Have the day's quote written and save it. Does nothing when the day has one."""
        if self._store.load(day):
            return
        line, by = await self._writer.write(day, self._store.before(day, self.RECENT_DAYS))
        quote = Quote(day=day, line=line, by=by)  # ValueError when it would not sit well in the widget
        self._store.save(quote)
        log.info("quote of %s: %s (%s)", day, quote.line, quote.by)
