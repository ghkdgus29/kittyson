# kittyson 코드 읽는 순서

요청 하나가 지나가는 길을 먼저 읽고, 그 요청이 읽어 가는 하루치(고양이, 명언)가 만들어지는 길을 그다음에 읽는다. 뼈대인 [main.py](src/kittyson/main.py)에서 시작해 호출되는 모듈로 내려가고, 화면 쪽(웹, 아이폰, 워치)은 마지막에 본다.

```
브라우저 / 아이폰 앱·위젯 / 워치 앱·컴플리케이션   (모두 같은 두 경로를 쓴다)
   │  GET /api/today, /cat/today.jpg
   ▼
main.py ──┬─ clock.py        시각, 날짜, 요일
          ├─ weather.py      Open-Meteo, 30분 캐시
          ├─ quote.py        오늘의 명언을 읽는다 (DailyQuote.get)
          └─ cats/daily.py   오늘의 고양이를 읽는다 (DailyCat.get)

scheduler.py (매일 23:00, 내일 것을 만든다)
          ├─ cats/daily.py   DailyCat.make
          │      ├─ cats/pixabay.py   사진을 가져오는 곳
          │      ├─ cats/check.py     고양이가 맞는지 확인 (claude.py 사용)
          │      ├─ images.py         정사각형으로 자르기
          │      └─ theme.py          사진에 맞는 글자색
          ├─ quote.py        DailyQuote.make
          │      └─ claude.py         Claude에게 묻는 단 하나의 함수
          └─ notify.py       만들지 못하면 텔레그램 알림

store.py   날짜별 기록 파일 (고양이와 명언이 같이 쓴다)
```

서버는 전날 밤에 다음 날의 고양이 사진과 명언을 만들어 둔다. 요청이 오면 JSON 하나(화면에 그릴 줄과, 사진에 맞는 글자색)와 사진 한 장을 내준다. 화면 쪽은 그 둘을 받아 그리기만 한다.

경로가 둘인 것은 내용이 바뀌는 주기가 달라서다. `/api/today` 는 요청마다 달라지고(시각, 날씨), 사진은 하루에 한 번 바뀐다. 그래서 화면 쪽은 `/api/today` 의 `cat.day` 가 바뀔 때만 사진을 새로 받는다. 요청은 아무것도 만들지 않고 저장된 것을 읽기만 하므로 기다릴 일이 없다.

## 1. 무엇을 만드는지: README

[README.md](README.md)에서 JSON 모양과 경로 표만 확인한다. 아이폰과 워치가 무엇을 보여 주는지는 [clients/apple/README.md](clients/apple/README.md)에 있다.

## 2. 뼈대: schemas.py → main.py → deps.py

- [schemas.py](src/kittyson/schemas.py): 응답 모양 전부다. `Widget` 이 화면에 그리는 줄이고, 필드 순서(`time`, `date`, `weekday`, `weather`, `quote`, `by`)가 곧 화면에 보이는 키 순서다. `Today` 는 거기에 고양이(`TodayCat`: 날짜, 출처, 글자색)를 더한 것이다.
- [main.py](src/kittyson/main.py): `/api/today` 핸들러 `today()` 를 읽는다. 인자 `weather: WeatherDep`, `cats: DailyCatDep`, `quotes: DailyQuoteDep` 가 이 핸들러가 쓰는 객체다. 줄은 `lines()` 가 만든다. `/cat/today.jpg` 는 같은 `DailyCat.get` 으로 고양이를 찾아 그 사진 파일을 준다. 아래쪽 `/api/widget` 과 `/cat/today.json` 은 앱스토어의 1.0 앱이 쓰는 예전 경로다.
- [deps.py](src/kittyson/deps.py): 그 객체들이 만들어지는 곳이다. `get_http_client`, `get_weather_service`, `get_daily_cat`, `get_daily_quote`, `get_scheduler` 가 각각 한 번만 만들어 모든 요청이 같이 쓴다(`@lru_cache`). 바깥으로 나가는 세 가지가 여기서 정해진다: 사진을 가져올 곳(`cat_source`), 명언을 쓸 곳(`quote_writer`), 알림을 보낼 곳(`notifier`). 테스트는 이 세 함수를 가짜로 바꿔 끼운다.
- `lifespan`(main.py)은 서버가 뜰 때 로그를 설정하고(`logs.configure`), `deps.startup()` 으로 객체를 미리 만들고 스케줄러를 돌린다. 내려갈 때 `deps.shutdown()` 이 스케줄러를 멈추고 HTTP 클라이언트를 닫는다.
- 설정값이 궁금해지면 [config.py](src/kittyson/config.py)를 참고한다. `settings` 하나를 가져다 쓰고, 모든 값은 `KITTYSON_*` 환경 변수로 바꿀 수 있다.

## 3. 단순한 모듈: clock, weather

`lines()` 가 부르는 순서대로 본다.

- [clock.py](src/kittyson/clock.py): 설정된 시간대의 현재 시각과 문자열 변환.
- [weather.py](src/kittyson/weather.py): `WeatherService.line` → `current`. 30분 캐시와, 실패하면 마지막 성공값을 유지하는 부분만 보면 된다. `WMO` 표는 훑고 넘어간다.

명언(`quotes.get`)은 6번에서 본다.

## 4. 핵심: store.py → scheduler.py → cats/

하루치가 만들어지는 길이다. 고양이와 명언은 같은 모양이다. 날짜별 기록(`Cat`, `Quote`)이 있고, 그것을 읽어 주는 `get(day)` 와 만들어 저장하는 `make(day)` 가 있다. 요청은 `get` 만 부르고, `make` 는 스케줄러만 부른다.

- [store.py](src/kittyson/store.py): 날짜마다 기록 하나(`YYYY-MM-DD.json`). 날짜별 파일이 어디 있는지 아는 곳은 여기뿐이다. `DayRecord` 가 기록의 바탕이고, `DayStore` 의 `load`, `save`, `before` 를 본다. 한 번 읽은 기록은 메모리에 둔다.
- [scheduler.py](src/kittyson/scheduler.py): `tick` → `_make` → `_notify`. 맨 위 상수(`AT`, `RETRY`, `MAX_TRIES`)를 먼저 본다. 오늘 것이 없으면 오늘 것을, 23:00부터는 내일 것을 만든다. 실패하면 간격을 두 배씩 늘려 여섯 번까지 다시 해 보고, 처음 실패했을 때와 포기할 때 알림을 보낸다.
- [notify.py](src/kittyson/notify.py): 텔레그램 봇으로 메시지 하나. 보내지 못해도 예외를 내지 않고, 토큰이 로그에 남지 않게 한다.

그다음 [cats/daily.py](src/kittyson/cats/daily.py)를 `DailyCat` 의 메서드 순서대로 읽는다.

1. `get`: 그날의 기록을 읽는다. 없으면 그 전의 가장 최근 것을 준다.
2. `make`: 그날 것이 이미 있으면 아무것도 하지 않는다. 없으면 `Source.pick(seen)` 으로 사진을 받고 `_save` 를 스레드에서 돌린다(자르고 색을 재는 일이 CPU를 오래 쓴다).
3. `_save`: 정사각형으로 자르고, 글자색을 재고, 기록(`Cat`)과 사진을 같이 저장한다.
4. 같은 파일 위쪽의 `Cat`(기록의 필드: `source`, `id`, `skipped`, `theme`), `Source` 프로토콜, `CatStore`(사진 파일의 위치, 이미 쓴 사진의 `seen()`).

`make` 가 부르는 것들:

- [cats/pixabay.py](src/kittyson/cats/pixabay.py): `pick` 이 `cat` 검색 결과를 인기순으로 훑으며 이미 쓴 사진(`seen`)과 고양이가 아닌 사진을 건너뛰고, 처음 남는 사진을 고른다. 무작위가 없어서 같은 상태에서는 항상 같은 사진이다. 확인은 두 번이다. 태그가 고양이를 말하는지(`described_as_cat`), 그리고 Claude가 사진을 보고 고양이라고 하는지(`_is_cat`). Claude를 부를 수 없으면 태그만 믿는다. 키가 없으면 새 고양이를 만들지 못한다.
- [cats/check.py](src/kittyson/cats/check.py): 그 두 확인의 구현. `ClaudeCatChecker.look` 이 위젯에 보일 정사각형을 줄여 Claude에게 보여 준다.
- [images.py](src/kittyson/images.py): 가운데를 잘라 정사각형으로 만드는 `square`, JPEG로 바꾸는 `jpeg`.

## 5. 글자색: theme.py

[theme.py](src/kittyson/theme.py)는 아래에서 위로 읽는다. 맨 위 docstring이 알고리즘 요약이므로 그것부터 읽는다.

1. `Theme`: 결과의 모양. 필드 기본값이 사진이 없을 때의 색이다.
2. `analyze`: 전체 흐름. 밝은 글자와 어두운 글자 중 하나를 고르고 색을 정한다.
3. `_measure`: 사진을 작은 칸으로 줄여 밝기 표본과 주된 색상을 잰다. 글자가 덜 덮는 오른쪽 가장자리는 덜 센다.
4. `_readability`: 흰 글자와 검은 글자가 각각 얼마나 잘 읽히는지 점수를 낸다. 검은 글자는 `LIGHT_BIAS` 만큼 더 앞서야 뽑힌다.
5. `_pick_hue`, `_color`, `_percentile`: 필요할 때 찾아본다.

## 6. 명언: quote.py → claude.py

[quote.py](src/kittyson/quote.py)는 맨 위 docstring을 먼저 읽고 아래 순서로 본다.

1. `Quote`: 날짜별 기록. 명언(`line`)과 말한 사람(`by`), 그리고 길이 제한(`LIMITS`)이 여기 있다. 제한을 넘는 답은 저장되지 않는다.
2. `DailyQuote.get`: 저장된 명언이 있으면 그것을, 없으면 `fallback`(목록 `QUOTES` 에서 날짜 순서대로 하나)을 준다.
3. `DailyQuote.make`: `ClaudeQuoteWriter.write` 에게 날짜와 최근 60일의 명언(`recent`)을 주고, 받은 답을 `Quote` 로 검사해 `data/quotes/YYYY-MM-DD.json` 에 쓴다. 다시 시도하는 일은 스케줄러가 맡는다.
4. `ClaudeQuoteWriter`: Claude에게 보내는 글이 클래스 안에 있다(`SYSTEM`, `PROMPT`, `FIELDS`, `SCHEMA`). 날마다 찾아볼 분야가 날짜에 따라 바뀐다.

[claude.py](src/kittyson/claude.py)의 `ask` 는 Claude를 부르는 유일한 곳이다. 도구 없이 질문 하나를 보내고 스키마에 맞는 답 하나를 받는다. 명언(`ClaudeQuoteWriter`)과 고양이 확인(`ClaudeCatChecker`)이 같은 함수를 쓴다.

[logs.py](src/kittyson/logs.py)는 짧다. 로그가 stderr와 `data/logs/app.log` 두 곳에 남는 방법, 그리고 Pixabay 키가 든 URL이 로그에 남지 않도록 `httpx` 로그를 낮추는 줄을 본다.

## 7. 브라우저 화면: static/

[app.js](src/kittyson/static/app.js)는 맨 아래 열 줄이 시작점이다. 거기서 `poll` → `show` → `render` → `fit` 으로 따라간다.

- `poll`: 1분마다 `/api/today` 를 받는다. `widget` 은 줄로 그리고, `cat` 의 날짜가 바뀌었으면 사진을 새로 받아 글자색을 입힌다(`showCat`, `applyTheme`).
- `render`: JSON을 생긴 그대로 줄 단위로 그린다.
- `serverNow`, `wallClock`, `tick`: 서버 시각과 기기 시각의 차이를 기억해 `time` 을 1초마다 넘긴다.
- `fit`, `hasStub`: 카드에 꽉 차는 글자 크기를 찾는다.
- `setMode`, `tap`: 슬라이더의 모드 세 가지(JSON, 사진, 숫자 세기)와 터치로 숫자 세기.

[index.html](src/kittyson/static/index.html)과 [style.css](src/kittyson/static/style.css)는 필요할 때 참고한다.

## 8. 아이폰·애플워치: clients/apple/

타깃이 네 개다: 아이폰 앱, 아이폰 위젯, 워치 앱, 워치 컴플리케이션. `Shared/` 는 넷이 같이 쓰고, 나머지 폴더는 타깃마다 화면 하나씩이다. [project.yml](clients/apple/project.yml)에서 어느 타깃이 어느 폴더를 쓰는지만 먼저 본다. `Kittyson.xcodeproj` 와 `Config/*-Info.plist` 는 여기서 만들어지는 파일이라 읽지 않는다.

받아 오기와 그리기 (`Shared/`):

- [Server.swift](clients/apple/Shared/Server.swift): `refresh` 가 `/api/today` 와 사진을 받아 파일로 두고(`today.json`, `cat.jpg`), `cached` 가 그 파일로 `Snapshot` 을 만든다. 사진은 고양이의 날짜가 바뀔 때만 받는다. `latest` 는 위젯용으로, 15분 안에 물어봤으면 다시 묻지 않는다. `Snapshot.lines` 가 화면에 그릴 줄을 정한다(기기의 날짜, 타이머, 숫자). 워치에서는 날짜와 요일을 한 줄로 합친다(`short`).
- [Layout.swift](clients/apple/Shared/Layout.swift): 위쪽의 타입(`Field`, `Piece`, `Row`, `Fit`, `Rules`)을 먼저 보고 `fit` → `wrap` → `words` 순으로 읽는다. 웹의 `fit` 과 같은 일을 계산으로 한다. 워치용 규칙은 `Rules.compact`, 시계 값은 `Clock`.
- [JsonText.swift](clients/apple/Shared/JsonText.swift), [Card.swift](clients/apple/Shared/Card.swift): `Layout.fit` 의 결과를 그린다. `"time"` 은 시스템이 스스로 넘기는 타이머 글자라 위젯에서도 초가 흐른다(`colored`).
- [Timeline.swift](clients/apple/Shared/Timeline.swift): 두 위젯의 갱신. 30분마다 새 타임라인을 받고, 그 사이에는 `Clock.changes` 의 시각에만 다시 그린다.

화면 (타깃마다):

- [KittysonApp.swift](clients/apple/App/KittysonApp.swift): 아이폰 앱. 카드와 그 아래 사용법([Guide.swift](clients/apple/App/Guide.swift))을 보여 준다. 앱이 앞에 올 때마다(`task(id: phase)`) 서버에서 새로 받고 위젯을 다시 그리게 한다. `Guide.swift` 는 글뿐이라 `topics` 목록만 훑는다.
- [KittysonWidget.swift](clients/apple/Widget/KittysonWidget.swift): 아이폰 홈 화면 위젯. 가장 짧다.
- [Store.swift](clients/apple/Shared/Store.swift), [Counter.swift](clients/apple/Shared/Counter.swift), [Countdown.swift](clients/apple/Shared/Countdown.swift): 워치 앱의 모드, 숫자 세기, 타이머 규칙. 화면 코드가 없어서 [Tests/main.swift](clients/apple/Tests/main.swift)의 Counter, Countdown 부분과 같이 읽는다.
- [KittysonWatchApp.swift](clients/apple/WatchApp/KittysonWatchApp.swift): `Screen.body` 를 먼저, 그다음 `tap`, `hold`, `slot`, `timerLine`, `set`. 크라운이 모드를 고를 때와 타이머 시간을 바꿀 때를 `setting` 하나로 나눈다.
- [Alarm.swift](clients/apple/WatchApp/Alarm.swift): 타이머가 끝날 때 울리는 알람 세션. `timer` 의 `didSet` → `schedule`. 세션이 사라지면 타이머도 지운다.
- [KittysonWatchWidget.swift](clients/apple/WatchWidget/KittysonWatchWidget.swift): 컴플리케이션 네 가지 모양.

[clients/apple/store/](clients/apple/store/README.md)와 [PRIVACY.md](PRIVACY.md)는 App Store에 올릴 글이다. 코드는 없다.

## 9. 테스트와 배포

- [tests/](tests/): 동작 명세로 읽는다. `uv run pytest -v` 로 이름만 먼저 봐도 된다. [test_app.py](tests/test_app.py)의 `data` 픽스처가 바깥으로 나가는 것들을 가짜로 바꿔 끼우는 방법을 보여 준다(`deps` 의 세 함수는 `monkeypatch`, 날씨는 `dependency_overrides`). 가짜 사진 출처와 가짜 명언 작성자는 [conftest.py](tests/conftest.py)에 있다. [test_scheduler.py](tests/test_scheduler.py), [test_notify.py](tests/test_notify.py), [test_cats.py](tests/test_cats.py), [test_pixabay.py](tests/test_pixabay.py)는 4번, [test_theme.py](tests/test_theme.py)는 5번, [test_quote.py](tests/test_quote.py)는 6번과 같이 보면 좋다.
- 스위프트 쪽 점검은 `clients/apple` 에서 돌린다.
  ```sh
  swiftc Shared/Counter.swift Shared/Countdown.swift Shared/Layout.swift Tests/main.swift -o /tmp/kittyson-check && /tmp/kittyson-check
  ```
- 배포: [Dockerfile](Dockerfile) → [docker-compose.yml](docker-compose.yml) → [.github/workflows/main.yml](.github/workflows/main.yml)

## 읽으면서 잡을 흐름

- **무작위가 없다.** 고양이는 아직 쓰지 않은 사진 중 인기순으로 첫 장이고, 명언을 찾아볼 분야와 `QUOTES` 의 한 줄은 날짜 순서대로 돈다. 같은 상태에서는 항상 같은 결과가 나온다.
- **디스크가 정답이다.** 그날의 고양이는 `data/cats/daily/YYYY-MM-DD.jpg` 와 `.json` 으로, 그날의 명언은 `data/quotes/YYYY-MM-DD.json` 으로 확정된다. 서버를 다시 띄워도 같은 값이 나온다. 다시 뽑으려면 파일을 지우고 서버를 다시 띄운다(읽은 기록은 메모리에 남아 있다). 아이폰과 워치도 마지막 응답을 파일로 두고 그것을 그린다.
- **만드는 일과 읽는 일이 나뉘어 있다.** `make` 는 스케줄러만 부르고, 요청은 `get` 으로 읽기만 한다. 그래서 요청은 Pixabay나 Claude를 기다리지 않는다.
- **층마다 폴백이 있다.** 그날 고양이가 없으면 가장 최근 고양이, 명언이 없으면 목록 `QUOTES` 의 한 줄, 날씨는 마지막 성공값, 고양이 확인은 태그, 앱은 디스크에 둔 마지막 응답을 쓴다. 만들기가 실패하면 스케줄러가 다시 해 보고 알림을 보낸다.
- **글자색은 서버가 한 번만 계산한다.** `DailyCat._save` 가 `theme` 을 그날의 기록에 저장한다. 화면과 위젯은 받은 색을 그대로 칠한다.
- **같은 규칙이 두 번 나온다.** 웹과 애플 클라이언트가 각자 구현한다. 한쪽을 고치면 다른 쪽도 확인한다: 글자 크기와 줄바꿈(`app.js` 의 `fit`, `hasStub` / `Layout.swift` 의 `fit`, `wrap`), 숫자 세기(`app.js` 의 `tap` / `Counter.swift`), 글자색 기본값(`style.css` 의 `:root` / `Server.swift` 의 `Theme` / `theme.py` 의 `Theme` 필드 기본값).
