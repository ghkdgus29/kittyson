# 코드 읽는 순서

kittyson 코드를 직접 읽으며 확인할 때의 순서다. 분량은 서버 파이썬 약 1,000줄, 웹 화면 약 360줄, 애플 클라이언트 스위프트 약 800줄이고, 테스트가 따로 700줄쯤 있다.

## 전체 그림

```
Open-Meteo (날씨) ──┐
사진 폴더 / cataas ──┼─ 서버 (src/kittyson) ─┬─ /api/widget ─────┬─ 웹 화면 (src/kittyson/static)
Claude (명언) ──────┘                        ├─ /cat/today.jpg ──┤
                                             └─ /cat/today.json ─┴─ 아이폰·워치 (clients/apple)
```

서버는 JSON 한 개와 사진 한 장, 그 사진에 맞는 글자색을 내준다. 화면 쪽(웹, 아이폰, 워치)은 그 세 가지를 받아 그리기만 한다. 그래서 서버를 먼저 읽고, 같은 일을 가장 짧게 하는 웹 화면을 읽은 뒤, 애플 클라이언트를 읽는다.

## 읽는 방법

- **파일 맨 위 주석부터 읽는다.** 파일마다 맨 위에 그 파일이 하는 일이 적혀 있다. 그것만 훑어도 전체 구조가 잡힌다.
- **위에서 아래로 읽지 말고 호출을 따라간다.** 요청이 들어오는 곳에서 시작해 불리는 함수로 내려간다. 아래 표의 "따라갈 길"이 그 순서다.
- **서버를 켜 놓고 읽는다.** 코드에서 본 것이 실제 응답과 파일로 어떻게 나오는지 바로 확인한다.
  ```sh
  uv run uvicorn kittyson.main:app --reload
  curl localhost:8000/api/widget
  curl localhost:8000/cat/today.json
  ls data/cats/daily data/quotes data/logs
  ```
- **모듈을 읽은 뒤 그 모듈의 테스트를 읽는다.** 테스트 이름이 그 모듈이 지켜야 하는 규칙 목록이다. `uv run pytest -v` 로 이름만 먼저 봐도 된다.

## 1. 서버

| 순서 | 파일 | 줄 | 따라갈 길, 확인할 것 |
|---|---|---|---|
| 1 | [schemas.py](src/kittyson/schemas.py) | 11 | JSON의 모양 전부. 키 순서가 곧 화면 순서다 |
| 2 | [main.py](src/kittyson/main.py) | 77 | 경로 다섯 개. `widget()` 이 다섯 값을 어디서 가져오는지, `lifespan` 이 시작할 때 무엇을 하는지 |
| 3 | [deps.py](src/kittyson/deps.py) | 69 | 날씨, 고양이, 명언 객체를 한 번만 만들어 모든 요청이 같이 쓰는 방법. 고양이를 어디서 받아 올지 정하는 목록도 여기 있다 |
| 4 | [config.py](src/kittyson/config.py), [clock.py](src/kittyson/clock.py) | 50, 28 | 설정값과 `KITTYSON_*` 환경 변수, 시간대 처리 |
| 5 | [weather.py](src/kittyson/weather.py) | 105 | `line()` → `current()`. 30분 캐시와, 실패하면 마지막 값을 그대로 쓰는 부분. 위쪽 `WMO` 표는 훑기만 한다 |
| 6 | [cats/base.py](src/kittyson/cats/base.py) | 149 | `get()` → `cached()` → `_make()` → `_fetch()`. 같은 날에는 같은 고양이가 나오는 이유(날짜로 정한 난수와 `daily/` 파일), 모두 실패하면 `latest()`, `VERSION` 의 역할 |
| 7 | [cats/local.py](src/kittyson/cats/local.py), [cats/cataas.py](src/kittyson/cats/cataas.py), [images.py](src/kittyson/images.py) | 29, 26, 20 | 사진을 주는 두 곳과 정사각형으로 자르기. `weight()` 가 0이면 그날 후보에서 빠진다 |
| 8 | [theme.py](src/kittyson/theme.py) | 179 | 맨 아래 `analyze()` 부터 읽고 `_measure()`, `_readability()`, `_pick_hue()`, `_color()` 로 올라간다. 맨 위 주석의 네 가지 규칙이 코드 어디에 있는지 짝지어 본다 |
| 9 | [quote.py](src/kittyson/quote.py) | 255 | `DailyQuote.line()` → `_start()` → `_write()` → `ClaudeWriter.write()` → `clean()`. `line()` 이 기다리지 않고 바로 답하는 것, 다시 시도하는 규칙(`_start`), 위쪽 상수들 |
| 10 | [logs.py](src/kittyson/logs.py) | 38 | 로그가 두 곳에 남는 방법 |

가장 긴 두 파일(`theme.py`, `quote.py`)은 뒤로 미뤘다. 앞의 일곱 단계만 읽어도 요청 하나가 처음부터 끝까지 어떻게 처리되는지 알 수 있다.

**테스트**는 [tests/test_app.py](tests/test_app.py)부터 읽는다. `client` 픽스처가 진짜 날씨와 Claude를 가짜로 바꿔 끼우는 방법(`dependency_overrides`)을 보여 준다. 나머지는 모듈과 이름이 같다: `test_cats.py`, `test_theme.py`, `test_quote.py`, `test_weather.py`, `test_logs.py`, `test_clock.py`.

## 2. 웹 화면

| 순서 | 파일 | 줄 | 따라갈 길, 확인할 것 |
|---|---|---|---|
| 1 | [index.html](src/kittyson/static/index.html) | 25 | 요소 네 개: 카드, 배경 사진, JSON, 모드 슬라이더 |
| 2 | [app.js](src/kittyson/static/app.js) | 197 | **맨 아래 열 줄이 시작점이다.** 거기서 `poll()` → `show()` → `render()` → `fit()` 으로 따라간다. 그다음 시계(`tick`, `scheduleTick`, `serverNow`), 모드와 숫자 세기(`setMode`, `tap`), 사진과 글자색(`showBackground`, `showTheme`) |
| 3 | [style.css](src/kittyson/static/style.css) | 137 | 글자색 변수(`:root`), 줄바꿈과 들여쓰기(`.json .line`), 모드별 모양 |

`fit()` 은 "칸에 들어가는 가장 큰 글자 크기"를 찾는다. 애플 클라이언트의 `Layout.fit` 이 같은 일을 하므로, 여기서 이해해 두면 다음 단계가 쉽다.

## 3. 아이폰·애플워치

먼저 [clients/apple/README.md](clients/apple/README.md)에서 타깃 네 개와 워치 앱의 동작을 읽는다. 코드는 무엇을 하려는지 알고 읽어야 빠르다.

| 순서 | 파일 | 줄 | 따라갈 길, 확인할 것 |
|---|---|---|---|
| 1 | [project.yml](clients/apple/project.yml) | 103 | 타깃 네 개가 각각 어느 폴더를 쓰는지만 본다. `Shared/` 는 넷 모두가 쓴다 |
| 2 | [Layout.swift](clients/apple/Shared/Layout.swift) 앞부분 | 50 | 타입만 먼저: `Field`, `Piece`, `Row`, `Fit`, `Rules`. 뒤의 모든 파일이 이 타입을 쓴다 |
| 3 | [Server.swift](clients/apple/Shared/Server.swift) | 139 | `refresh()` 가 서버의 세 경로를 받아 파일로 두고, `cached()` 가 그 파일로 `Snapshot` 을 만든다. `Snapshot.lines()` 가 화면에 그릴 줄을 정한다(날짜, 타이머, 숫자) |
| 4 | [Layout.swift](clients/apple/Shared/Layout.swift) 나머지 | 135 | `fit()` → `wrap()` → `words()`. 글자 폭을 세는 `units()`, 워치용 `Rules.compact`, 시계 값을 다루는 `Clock` |
| 5 | [Tests/main.swift](clients/apple/Tests/main.swift) | 106 | Layout 부분을 4번과 같이 읽는다. 숫자(17pt, 줄 수)가 어디서 나오는지 보인다 |
| 6 | [JsonText.swift](clients/apple/Shared/JsonText.swift), [Card.swift](clients/apple/Shared/Card.swift) | 74, 38 | `Layout.fit` 의 결과를 그리는 곳. `"time"` 이 스스로 흐르는 글자인 이유(`colored`), 사진 위에 JSON을 얹는 `Card` |
| 7 | [KittysonApp.swift](clients/apple/App/KittysonApp.swift), [KittysonWidget.swift](clients/apple/Widget/KittysonWidget.swift), [Timeline.swift](clients/apple/Shared/Timeline.swift) | 34, 19, 29 | 가장 단순한 화면 둘. 위젯이 30분마다 서버를 확인하는 방법 |
| 8 | [Store.swift](clients/apple/Shared/Store.swift), [Counter.swift](clients/apple/Shared/Counter.swift), [Countdown.swift](clients/apple/Shared/Countdown.swift) | 27, 19, 44 | 워치 앱의 모드, 숫자 세기, 타이머 규칙. 화면 코드가 없어서 `Tests/main.swift` 의 Counter, Countdown 부분과 같이 읽는다 |
| 9 | [KittysonWatchApp.swift](clients/apple/WatchApp/KittysonWatchApp.swift) | 105 | `Screen.body` 를 먼저, 그다음 `tap()`, `hold()`, `slot`, `timerLine()`, `set()`. 크라운이 모드를 고를 때와 타이머 시간을 바꿀 때를 `setting` 하나로 나누는 부분 |
| 10 | [Alarm.swift](clients/apple/WatchApp/Alarm.swift) | 49 | 타이머가 끝날 때 울리는 알람 세션. `timer` 의 `didSet` → `schedule()`, 세션이 사라지면 타이머도 지우는 이유 |
| 11 | [KittysonWatchWidget.swift](clients/apple/WatchWidget/KittysonWatchWidget.swift) | 43 | 컴플리케이션 네 가지 모양 |

읽으면서 돌려 볼 것:

```sh
cd clients/apple
swiftc Shared/Counter.swift Shared/Countdown.swift Shared/Layout.swift Tests/main.swift -o /tmp/kittyson-check && /tmp/kittyson-check
```

`Kittyson.xcodeproj` 와 `Config/*-Info.plist` 는 `project.yml` 에서 만들어지는 파일이라 읽지 않아도 된다.

## 4. 배포 (필요할 때)

[Dockerfile](Dockerfile), [docker-compose.yml](docker-compose.yml), [.github/workflows/main.yml](.github/workflows/main.yml) 순서로 읽는다. 설명은 [README.md](README.md)의 "배포"에 있다.

## 같은 규칙이 두 번 나오는 곳

웹과 애플 클라이언트는 같은 규칙을 각자 구현한다. 한쪽을 고치면 다른 쪽도 확인한다.

| 규칙 | 웹 | 애플 |
|---|---|---|
| 들어가는 가장 큰 글자, 줄바꿈 | `app.js` 의 `fit`, `hasStub` 과 `style.css` | `Layout.swift` 의 `fit`, `wrap` |
| 숫자 세기(한 번 +1, 두 번 −1, 세 번 0) | `app.js` 의 `tap` | `Counter.swift` |
| 글자색 기본값 | `style.css` 의 `:root` | `Server.swift` 의 `Theme` (서버는 `theme.py` 의 `DEFAULT`) |
