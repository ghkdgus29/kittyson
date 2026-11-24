# 2026-11-24에 바뀐 것

요청한 수정사항마다 무엇이 어떻게 바뀌었는지 적는다. 커밋은 `c5e52c4`.

## 고양이

| 요청 | 바뀐 것 |
| --- | --- |
| 저장 경로가 day가 들어간 `_path` 임을 암묵적으로 알아야 한다 | 날짜별 파일의 위치는 [store.py](src/kittyson/store.py)의 `DayStore` 만 안다. 다른 코드는 `load(day)`, `save(record)`, `before(day)` 로 날짜를 넘겨서 읽고 쓴다. 고양이와 명언이 같은 `DayStore` 를 쓴다. |
| theme, info가 dict이고 버전으로 관리된다 | 둘 다 필드가 있는 pydantic 모델이 됐다: `Cat`([cats/daily.py](src/kittyson/cats/daily.py)), `Theme`([theme.py](src/kittyson/theme.py)), `Quote`([quote.py](src/kittyson/quote.py)). 버전 번호와 버전에 따른 분기는 없앴다. |
| `save_square` 를 스레드풀로 빼기 | 자르고 글자색을 재는 `DailyCat._save` 를 `asyncio.to_thread` 로 돌린다. |
| 이미지 중복 검증 (id 필요) | 그날의 기록에 Pixabay 사진 id(`Cat.id`)와 건너뛴 사진의 id(`Cat.skipped`)를 남긴다. 새로 고를 때 지금까지의 id(`CatStore.seen()`)는 건너뛴다. |
| provider의 랜덤성 빼기 | 사진은 Pixabay에서만 가져온다(`cats/local.py`, `cats/cataas.py` 삭제). 인기순 검색 결과에서 아직 쓰지 않은 첫 고양이 사진을 고른다([cats/pixabay.py](src/kittyson/cats/pixabay.py)). 같은 상태에서는 항상 같은 사진이다. |
| 요청 때 만들지 말고 스케줄러로 매일 하나 만들어 두기 | [scheduler.py](src/kittyson/scheduler.py)가 매일 23:00에 다음 날의 고양이와 명언을 만든다. 서버가 뜰 때 오늘 것이 없으면 그것도 만든다. 요청은 저장된 것을 읽기만 한다(`get`). 만드는 일(`make`)은 스케줄러만 부른다. |
| 만들기에 실패하면 알림 받기 | 간격을 두 배씩 늘려 여섯 번까지 다시 해 본다. 처음 실패했을 때와 포기할 때 텔레그램으로 알린다([notify.py](src/kittyson/notify.py)). 그날 고양이가 없으면 가장 최근 고양이가 나온다. |
| 서빙 API를 (이미지만 빼고) 하나로 합치기 | `GET /api/today` 가 화면의 줄(`widget`)과 고양이(`cat`: 날짜, 출처, 글자색)를 한 번에 준다. 사진은 `GET /cat/today.jpg`. 예전 `/api/widget`, `/cat/today.json` 은 없앴다. |

## 명언

| 요청 | 바뀐 것 |
| --- | --- |
| 말한 사람도 보여 주기 | 별도 키 `"by"` 로 보여 준다. `Widget` 의 필드는 `time`, `date`, `weekday`, `weather`, `quote`, `by`. |
| 동기부여 위주로 | 프롬프트의 규칙을 도전, 끈기, 용기, 실행에 대한 말로 바꿨다. Claude를 쓸 수 없는 날에 나오는 목록 `QUOTES` 도 그런 명언 34개로, 말한 사람과 출처를 함께 적어 새로 골랐다. |
| 일부를 발췌하지 말고 전체 명언을 | 프롬프트가 처음부터 전체가 짧은 명언을 고르게 한다. 길이를 맞추려고 줄이거나 바꾸는 것을 금지했다. |
| 28자는 적다, 이름까지 3줄 안에 | 명언은 32자 이내로 요청하고 36자까지 받는다. 이름은 9자까지. 워치에서 명언이 세 줄, 이름이 한 줄이다. 넘는 답은 저장하지 않고 스케줄러가 다시 시도한다. |

## Claude writer

| 요청 | 바뀐 것 |
| --- | --- |
| 클래스 이름을 분명하게 | `ClaudeWriter` 는 `ClaudeQuoteWriter` 로, `ClaudeChecker` 는 `ClaudeCatChecker` 로 바꿨다. |
| 프롬프트를 전역 변수 말고 클래스 안으로 | `ClaudeQuoteWriter` 안의 `SYSTEM`, `PROMPT`, `FIELDS`, `SCHEMA`. 고양이 확인도 같은 식이다([cats/check.py](src/kittyson/cats/check.py)). |

## 화면 쪽

| 요청 | 바뀐 것 |
| --- | --- |
| 앱 코드도 지금 전환 | 웹([app.js](src/kittyson/static/app.js))과 애플 클라이언트([Server.swift](clients/apple/Shared/Server.swift))가 `/api/today` 하나를 받는다. 사진은 고양이의 날짜가 바뀔 때만 새로 받는다. 애플 쪽은 다음 빌드부터 적용된다. |
| 워치 글자가 작아지지 않게 | `by` 로 줄이 하나 늘어난 만큼, 워치에서는 날짜와 요일을 한 줄로 합쳤다: `"d": "26-11-24 화"`. 날씨는 띄어쓰기를 둔 채 두 줄이다. 46mm에서 명언이 27자 이하면 17pt. |

## 파일

- 새로 생긴 것: `store.py`, `scheduler.py`, `notify.py`, `cats/daily.py`, `tests/test_scheduler.py`, `tests/test_notify.py`
- 없어진 것: `cats/base.py`, `cats/local.py`, `cats/cataas.py`
- 새 설정: `KITTYSON_TELEGRAM_TOKEN`, `KITTYSON_TELEGRAM_CHAT` (둘 다 있어야 알림을 보낸다)

## 아직 안 한 것

- 리팩터링 전에 저장된 고양이 기록에는 사진 id가 없다. 그 사진들은 다시 뽑힐 수 있다.
- theme 분석의 알고리즘은 그대로다. 결과가 `Theme` 모델이 된 것만 바뀌었다.
