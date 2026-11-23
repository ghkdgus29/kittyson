# kittyson 코드 읽는 순서

요청 하나가 지나가는 길을 따라 읽는다. 뼈대인 [main.py](src/kittyson/main.py)에서 시작해 호출되는 모듈로 내려가고, 화면 쪽(웹, 아이폰, 워치)은 마지막에 본다.

```
브라우저 / 아이폰 앱·위젯 / 워치 앱·컴플리케이션   (모두 같은 세 경로를 쓴다)
   │  GET /api/widget, /cat/today.jpg, /cat/today.json
   ▼
main.py ──┬─ clock.py      시각, 날짜, 요일
          ├─ weather.py    Open-Meteo, 30분 캐시
          ├─ quote.py      오늘의 명언 (DailyQuote)
          │      └─ claude.py                       Claude에게 묻는 단 하나의 함수
          └─ cats/base.py  오늘의 고양이 (DailyCat)
                 ├─ cats/local.py, cats/pixabay.py, cats/cataas.py   사진을 가져오는 곳
                 ├─ cats/check.py                   고양이가 맞는지 확인 (claude.py 사용)
                 ├─ images.py                       정사각형으로 자르기
                 └─ theme.py                        사진에 맞는 글자색
```

서버는 JSON 하나와 사진 한 장, 그 사진에 맞는 글자색을 내준다. 화면 쪽은 그 세 가지를 받아 그리기만 한다.

경로가 셋인 것은 내용이 바뀌는 주기가 달라서다. `/api/widget`은 요청마다 달라지고, 사진과 글자색은 하루에 한 번 바뀐다. 그래서 화면 쪽은 사진을 날짜가 바뀔 때만 받는다. 또 `/api/widget`은 고양이를 기다리지 않으므로, 그날의 첫 사진을 받는 동안에도 바로 답한다.

## 1. 무엇을 만드는지: README

[README.md](README.md)에서 JSON 모양과 경로 5개만 확인한다. 아이폰과 워치가 무엇을 보여 주는지는 [clients/apple/README.md](clients/apple/README.md)에 있다.

## 2. 뼈대: schemas.py → main.py → deps.py

- [schemas.py](src/kittyson/schemas.py): 응답 모양 `Widget`. 필드 순서(`time`, `date`, `weekday`, `weather`, `quote`)가 곧 화면에 보이는 키 순서다.
- [main.py](src/kittyson/main.py): `/api/widget` 핸들러를 읽는다. 인자 `weather: WeatherDep`, `quote: DailyQuoteDep`가 이 핸들러가 쓰는 객체다. 고양이는 여기서 쓰지 않는다. `/cat/today.jpg`와 `/cat/today.json`이 `cats: DailyCatDep`를 받아 같은 `DailyCat.get`을 부른다.
- [deps.py](src/kittyson/deps.py): 그 객체들이 만들어지는 곳이다. `get_http_client`, `get_weather_service`, `get_daily_cat`, `get_daily_quote`가 각각 한 번만 만들어 모든 요청이 같이 쓴다(`@lru_cache`). 고양이를 어디서 가져올지도 `get_daily_cat`의 목록에 적혀 있다: 사진 폴더, 그리고 `KITTYSON_PIXABAY_KEY`가 있으면 Pixabay, 없으면 cataas.
- `lifespan`(main.py)은 서버가 뜰 때 로그를 설정하고(`logs.configure`), `data/` 아래 폴더를 만들고, `deps.startup()`으로 객체를 미리 만든다. 내려갈 때 `deps.shutdown()`이 쓰고 있던 명언 작업을 멈추고 HTTP 클라이언트를 닫는다.
- 설정값이 궁금해지면 [config.py](src/kittyson/config.py)를 참고한다. `settings` 하나를 가져다 쓰고, 모든 값은 `KITTYSON_*` 환경 변수로 바꿀 수 있다.

## 3. 단순한 모듈: clock, weather

`/api/widget` 핸들러가 부르는 순서대로 본다.

- [clock.py](src/kittyson/clock.py): 설정된 시간대의 현재 시각과 문자열 변환.
- [weather.py](src/kittyson/weather.py): `WeatherService.line` → `current`. 30분 캐시와, 실패하면 마지막 성공값을 유지하는 부분만 보면 된다. `WMO` 표는 훑고 넘어간다.

명언(`quote.line`)은 6번에서 본다.

## 4. 핵심: cats/base.py

[cats/base.py](src/kittyson/cats/base.py)는 파일 위에서부터 읽지 말고 `DailyCat`의 메서드를 호출 순서대로 읽는다.

1. `get`: 캐시 확인 → 락 → 다시 확인 → `_make`
2. `cached`: 디스크의 `.jpg`와 `.json`이 있고, `.json`의 `v`가 지금 `VERSION`과 같을 때만 그날의 고양이로 친다.
3. `_make`: 다른 버전이 저장한 `.json`이 있으면 사진은 그대로 두고 글자색만 다시 읽는다. 없으면 `_fetch`로 사진을 받는다. 끝에 `.json`(`v`, `source`, `theme`)을 쓴다.
4. `_fetch`: 날짜 시드로 provider 하나를 고르고, 실패하면 나머지를 목록 순서대로 시도한다. 받은 사진은 정사각형으로 저장한다.
5. `latest`: 모든 provider가 실패했을 때 쓰는 이전 날 고양이. 버전은 따지지 않는다.

그다음 `_fetch`가 부르는 것들을 본다.

- `Provider` 프로토콜 (같은 파일 위쪽): `weight()`와 `pick()`. `weight()`가 0이면 그날 후보에서 빠진다.
- [cats/local.py](src/kittyson/cats/local.py): `data/cats/inbox/`의 사진. 비어 있으면 `weight()`가 0이다.
- [cats/pixabay.py](src/kittyson/cats/pixabay.py): `pick`이 `cat`으로 검색하고, 고양이가 아닌 사진을 걸러 가며 최대 5장까지 본다. 확인은 두 번이다. 태그가 고양이를 말하는지(`described_as_cat`), 그리고 Claude가 사진을 보고 고양이라고 하는지(`_is_cat`). Claude를 부를 수 없으면 태그만 믿는다.
- [cats/check.py](src/kittyson/cats/check.py): 그 두 확인의 구현. `ClaudeChecker.look`이 위젯에 보일 정사각형을 512px로 줄여 Claude에게 보여 준다.
- [cats/cataas.py](src/kittyson/cats/cataas.py): cataas.com에서 한 장. Pixabay 키가 없을 때만 쓰인다.
- [images.py](src/kittyson/images.py): 가운데를 잘라 정사각형으로 저장.

## 5. 글자색: theme.py

[theme.py](src/kittyson/theme.py)는 아래에서 위로 읽는다. 맨 위 docstring이 알고리즘 요약이므로 그것부터 읽는다.

1. `for_file` → `analyze`: 전체 흐름. 밝은 글자와 어두운 글자 중 하나를 고르고 색을 정한다.
2. `_measure`: 사진을 48×48 칸으로 줄여 밝기 표본과 주된 색상을 잰다. 글자가 덜 덮는 오른쪽 가장자리는 덜 센다.
3. `_readability`: 흰 글자와 검은 글자가 각각 얼마나 잘 읽히는지 점수를 낸다. 검은 글자는 `LIGHT_BIAS`만큼 더 앞서야 뽑힌다.
4. `_pick_hue`, `_color`, `_percentile`: 필요할 때 찾아본다.

## 6. 명언: quote.py → claude.py

[quote.py](src/kittyson/quote.py)는 `DailyQuote`의 메서드를 호출 순서대로 읽는다. 맨 위 docstring과 상수(`MAX_CHARS`, `RETRY_SECONDS`, `MAX_TRIES`)를 먼저 본다.

1. `line`: 저장된 명언이 있으면 그것을, 없으면 `_start`로 쓰기를 시작해 놓고 `quote_for`(목록 `QUOTES`에서 날짜 시드로 고른 한 줄)를 바로 돌려준다. 요청은 Claude를 기다리지 않는다.
2. `_start`: 한 번에 하나만 돌리고, 하루에 3번까지, 30분 간격으로만 다시 시도한다.
3. `_write`: `ClaudeWriter.write`에게 날짜와 최근 60일의 명언(`recent`)을 주고, 받은 문장을 `clean`으로 검사한 뒤 `data/quotes/YYYY-MM-DD.json`에 쓴다(`line`, `by`, `source`).
4. `build_prompt`, `PROMPT`, `FIELDS`: Claude에게 보내는 글. 날마다 찾아볼 분야가 날짜 시드로 바뀐다.

[claude.py](src/kittyson/claude.py)의 `ask`는 Claude를 부르는 유일한 곳이다. 도구 없이 질문 하나를 보내고 스키마에 맞는 답 하나를 받는다. 명언(`ClaudeWriter`)과 고양이 확인(`ClaudeChecker`)이 같은 함수를 쓴다.

[logs.py](src/kittyson/logs.py)는 짧다. 로그가 stderr와 `data/logs/app.log` 두 곳에 남는 방법, 그리고 Pixabay 키가 든 URL이 로그에 남지 않도록 `httpx` 로그를 낮추는 줄을 본다.

## 7. 브라우저 화면: static/

[app.js](src/kittyson/static/app.js)는 맨 아래 열 줄이 시작점이다. 거기서 `poll` → `show` → `render` → `fit` 으로 따라간다.

- `poll`: 1분마다 `/api/widget`을 받고, 날짜가 바뀌면 사진(`showBackground`)과 글자색(`showTheme`)을 새로 받는다.
- `render`: JSON을 생긴 그대로 줄 단위로 그린다.
- `serverNow`, `wallClock`, `tick`: 서버 시각과 기기 시각의 차이를 기억해 `time`을 1초마다 넘긴다.
- `fit`, `hasStub`: 카드에 꽉 차는 글자 크기를 찾는다.
- `setMode`, `tap`: 슬라이더의 모드 세 가지(JSON, 사진, 숫자 세기)와 터치로 숫자 세기.

[index.html](src/kittyson/static/index.html)과 [style.css](src/kittyson/static/style.css)는 필요할 때 참고한다.

## 8. 아이폰·애플워치: clients/apple/

타깃이 네 개다: 아이폰 앱, 아이폰 위젯, 워치 앱, 워치 컴플리케이션. `Shared/`는 넷이 같이 쓰고, 나머지 폴더는 타깃마다 화면 하나씩이다. [project.yml](clients/apple/project.yml)에서 어느 타깃이 어느 폴더를 쓰는지만 먼저 본다. `Kittyson.xcodeproj`와 `Config/*-Info.plist`는 여기서 만들어지는 파일이라 읽지 않는다.

받아 오기와 그리기 (`Shared/`):

- [Server.swift](clients/apple/Shared/Server.swift): `refresh`가 서버의 세 경로를 받아 파일로 두고(`widget.json`, `theme.json`, `cat.jpg`), `cached`가 그 파일로 `Snapshot`을 만든다. 사진은 하루에 한 번만 받는다. `latest`는 위젯용으로, 15분 안에 물어봤으면 다시 묻지 않는다. `Snapshot.lines`가 화면에 그릴 줄을 정한다(기기의 날짜, 타이머, 숫자).
- [Layout.swift](clients/apple/Shared/Layout.swift): 위쪽의 타입(`Field`, `Piece`, `Row`, `Fit`, `Rules`)을 먼저 보고 `fit` → `wrap` → `words` 순으로 읽는다. 웹의 `fit`과 같은 일을 계산으로 한다. 워치용 규칙은 `Rules.compact`, 시계 값은 `Clock`.
- [JsonText.swift](clients/apple/Shared/JsonText.swift), [Card.swift](clients/apple/Shared/Card.swift): `Layout.fit`의 결과를 그린다. `"time"`은 시스템이 스스로 넘기는 타이머 글자라 위젯에서도 초가 흐른다(`colored`).
- [Timeline.swift](clients/apple/Shared/Timeline.swift): 두 위젯의 갱신. 30분마다 새 타임라인을 받고, 그 사이에는 `Clock.changes`의 시각에만 다시 그린다.

화면 (타깃마다):

- [KittysonApp.swift](clients/apple/App/KittysonApp.swift): 아이폰 앱. 카드와 그 아래 사용법([Guide.swift](clients/apple/App/Guide.swift))을 보여 준다. 앱이 앞에 올 때마다(`task(id: phase)`) 서버에서 새로 받고 위젯을 다시 그리게 한다. `Guide.swift`는 글뿐이라 `topics` 목록만 훑는다.
- [KittysonWidget.swift](clients/apple/Widget/KittysonWidget.swift): 아이폰 홈 화면 위젯. 가장 짧다.
- [Store.swift](clients/apple/Shared/Store.swift), [Counter.swift](clients/apple/Shared/Counter.swift), [Countdown.swift](clients/apple/Shared/Countdown.swift): 워치 앱의 모드, 숫자 세기, 타이머 규칙. 화면 코드가 없어서 [Tests/main.swift](clients/apple/Tests/main.swift)의 Counter, Countdown 부분과 같이 읽는다.
- [KittysonWatchApp.swift](clients/apple/WatchApp/KittysonWatchApp.swift): `Screen.body`를 먼저, 그다음 `tap`, `hold`, `slot`, `timerLine`, `set`. 크라운이 모드를 고를 때와 타이머 시간을 바꿀 때를 `setting` 하나로 나눈다.
- [Alarm.swift](clients/apple/WatchApp/Alarm.swift): 타이머가 끝날 때 울리는 알람 세션. `timer`의 `didSet` → `schedule`. 세션이 사라지면 타이머도 지운다.
- [KittysonWatchWidget.swift](clients/apple/WatchWidget/KittysonWatchWidget.swift): 컴플리케이션 네 가지 모양.

[clients/apple/store/](clients/apple/store/README.md)와 [PRIVACY.md](PRIVACY.md)는 App Store에 올릴 글이다. 코드는 없다.

## 9. 테스트와 배포

- [tests/](tests/): 동작 명세로 읽는다. `uv run pytest -v`로 이름만 먼저 봐도 된다. [test_app.py](tests/test_app.py)의 `client` 픽스처가 진짜 날씨와 Claude를 가짜로 바꿔 끼우는 방법(`dependency_overrides`)을 보여 준다. [test_cats.py](tests/test_cats.py)와 [test_pixabay.py](tests/test_pixabay.py)는 4번, [test_theme.py](tests/test_theme.py)는 5번, [test_quote.py](tests/test_quote.py)는 6번과 같이 보면 좋다.
- 스위프트 쪽 점검은 `clients/apple`에서 돌린다.
  ```sh
  swiftc Shared/Counter.swift Shared/Countdown.swift Shared/Layout.swift Tests/main.swift -o /tmp/kittyson-check && /tmp/kittyson-check
  ```
- 배포: [Dockerfile](Dockerfile) → [docker-compose.yml](docker-compose.yml) → [.github/workflows/main.yml](.github/workflows/main.yml)

## 읽으면서 잡을 흐름

- **날짜가 시드다.** `random.Random(f"provider:{day}")`, `random.Random(f"quote:{day}")`, `random.Random(f"field:{day}")` 덕분에 같은 날은 항상 같은 결과가 나온다.
- **디스크가 정답이다.** 오늘의 고양이는 `data/cats/daily/YYYY-MM-DD.jpg`와 `.json`으로, 오늘의 명언은 `data/quotes/YYYY-MM-DD.json`으로 확정된다. 서버를 다시 띄워도 같은 값이 나오고, 파일을 지우면 다시 뽑는다. 아이폰과 워치도 마지막 응답을 파일로 두고 그것을 그린다.
- **층마다 폴백이 있다.** 고양이는 시드로 고른 provider → 나머지 provider → `latest()` 순이다. 날씨는 마지막 성공값, 명언은 목록 `QUOTES`의 한 줄, 고양이 확인은 태그, 앱은 디스크에 둔 마지막 응답을 쓴다.
- **느린 일은 요청을 붙잡지 않는다.** 명언은 뒤에서 쓰고 그동안 목록의 한 줄을 보여 준다. 고양이 사진만 그날의 첫 요청이 기다린다(락 하나로 한 번만 받는다).
- **글자색은 서버가 한 번만 계산한다.** `_make`가 `theme`을 `.json`에 저장하고, [cats/base.py](src/kittyson/cats/base.py)의 `VERSION`이 바뀌면 같은 사진으로 다시 계산한다. 화면과 위젯은 받은 색을 그대로 칠한다.
- **같은 규칙이 두 번 나온다.** 웹과 애플 클라이언트가 각자 구현한다. 한쪽을 고치면 다른 쪽도 확인한다: 글자 크기와 줄바꿈(`app.js`의 `fit`, `hasStub` / `Layout.swift`의 `fit`, `wrap`), 숫자 세기(`app.js`의 `tap` / `Counter.swift`), 글자색 기본값(`style.css`의 `:root` / `Server.swift`의 `Theme` / `theme.py`의 `DEFAULT`).
