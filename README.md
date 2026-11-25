# kittyson

kitty + JSON. 매일 바뀌는 고양이 배경 위에 위젯 JSON을 생긴 그대로 띄우는 화면.

```json
{
  "time": "14:01:53",
  "date": "2026-11-10",
  "weekday": "화요일",
  "weather": "☁️ 11° ↑14 ↓6",
  "quote": "천 리 길도 한 걸음부터 시작된다",
  "by": "노자"
}
```

## 실행

```sh
uv sync
uv run uvicorn kittyson.main:app --reload   # http://localhost:8000
uv run pytest
```

| 경로 | 설명 |
|---|---|
| `/` | 화면 (정사각형 카드) |
| `/api/today` | 사진을 뺀 오늘 전부. `widget` 은 위 JSON이고(`time`, `date` 는 요청 순간의 서버 시각, 24시간제), `cat` 은 사진의 날짜와 출처, 그 사진 위에서 잘 읽히는 글자색(`theme`)이다. 고양이가 아직 한 장도 없으면 `cat` 은 `null` |
| `/cat/today.jpg` | 오늘의 고양이, 1024×1024 |
| `/healthz` | 상태 |

## 하루치 미리 만들기

고양이와 명언은 요청이 들어올 때 만들지 않는다. [scheduler.py](src/kittyson/scheduler.py)가 전날 23:00에 다음 날 것을 만들어 두고, 요청은 저장된 것을 읽기만 한다.

- 스케줄러는 하루에 한 번, 23:00 정각에 돈다. 그때까지는 자고 있고, 중간에 확인하지 않는다.
- 서버가 켜질 때 한 번 더 돈다. 오늘 것이 없으면(처음 켰을 때, 밤새 꺼져 있었을 때) 그때 만든다.
- 실패하면 10분마다 다시 해서 모두 6번 시도한다(23:00, 23:10, 23:20, 23:30, 23:40, 23:50). 날이 바뀌기 전에 끝난다.
- 처음 실패했을 때와 6번 모두 실패했을 때 텔레그램으로 알린다([notify.py](src/kittyson/notify.py)). `.env` 에 `KITTYSON_TELEGRAM_TOKEN`(텔레그램의 @BotFather 에서 만든 봇의 토큰)과 `KITTYSON_TELEGRAM_CHAT`(알림을 받을 채팅의 id)이 있어야 하고, 없으면 로그에만 남는다.
- 끝내 못 만든 날에는 가장 최근 고양이와, 목록에 있는 명언이 대신 나온다.

## 고양이 사진

- 하루에 한 장을 [Pixabay](https://pixabay.com)에서 받아 온다([pixabay.py](src/kittyson/cats/pixabay.py)). 고양이 사진 검색 결과를 인기순으로 훑어, 아직 쓰지 않은 첫 사진을 고른다. 무작위로 고르지 않는다. 어느 날 어떤 사진이 나올지는 그 전에 쓴 사진들로 정해진다. 인기순 500장을 다 쓰면 최신순으로 넘어간다.
- `.env` 에 `KITTYSON_PIXABAY_KEY` 가 있어야 한다(무료, 로그인하면 [API 문서](https://pixabay.com/api/docs/)에 나온다). 없으면 새 고양이를 만들지 못한다.
- 같은 사진은 두 번 나오지 않는다. 날짜마다 `data/cats/daily/YYYY-MM-DD.json` 에 그 사진의 Pixabay id(`id`)와, 고르는 길에 고양이가 아니어서 넘긴 사진의 id(`skipped`)를 적어 두고, 새로 고를 때 이 id들을 건너뛴다([daily.py](src/kittyson/cats/daily.py)).
- 검색 결과에는 고양이가 아닌 사진도 섞여 있고, 정사각형이 아닌 사진은 양옆이 잘린다. 그래서 받기 전에 두 번 확인한다([check.py](src/kittyson/cats/check.py)). 사진 태그에 cat, kitten 같은 단어가 있고 lion, tiger 같은 단어가 없어야 하고, 그다음 Claude가 화면에 나갈 정사각형을 보고 고양이인지 답한다(기본 `claude-opus-5-5`, `KITTYSON_CAT_MODEL`). 고양이가 아니면 다음 사진으로 넘어가고, 한 번에 다섯 장까지 본다.
- Claude를 못 부르면(토큰 없음 등) 태그만 믿고 받는다. 인증은 아래 명언과 같다.
- 한 번 만든 날의 고양이는 바뀌지 않는다. 사진은 `data/cats/daily/YYYY-MM-DD.jpg`, 출처와 id, 글자색은 옆의 `.json` 이다.
- 그날 고양이를 바꾸고 싶으면 두 파일을 지우고 서버를 다시 시작한다. 그대로 지우면 그 사진의 id도 같이 사라져서 같은 사진이 다시 뽑힌다. 다른 사진을 원하면 지우기 전에 그 id를 다른 날 `.json` 의 `skipped` 에 적어 둔다.

## 오늘의 명언

`quote` 는 실제 인물이 남긴 동기부여 명언이고, `by` 는 그 말을 한 사람이다. Claude가 하루에 하나 고른다([quote.py](src/kittyson/quote.py)의 `ClaudeQuoteWriter`, Claude Agent SDK). 날짜·요일, 그날 찾아볼 분야(철학자, 운동선수, 한국 인물 등)와 최근 두 달의 명언을 넘겨서, 전과 겹치지 않는 명언을 받는다.

- 명언은 일부를 떼어 내지 않고 전체를 싣는다. 그래서 처음부터 짧은 명언을 고르게 한다. 32자 이내를 부탁하고, 36자를 넘는 명언과 9자를 넘는 이름은 저장하지 않고 실패로 친다(`Quote.LIMITS`). 46mm 워치에서 명언이 세 줄, 이름이 한 줄에 들어오는 길이다.
- Claude가 고른 명언은 따로 검증하지 않는다. 출처가 분명한 말만 고르라고 시키지만, 틀릴 수 있다. 의심스러우면 `by` 를 보고 확인한다.
- 전날 23:00에 골라 `data/quotes/YYYY-MM-DD.json` 에 확정한다(위의 "하루치 미리 만들기"). 고르기 전과 끝내 못 고른 날에는 출처를 확인해 둔 명언 목록(`QUOTES`, 줄마다 말한 사람과 출처가 적혀 있다)에서 날짜 순서대로 하나가 나온다.
- 인증은 `claude` CLI와 같다. 서버는 `.env` 의 `CLAUDE_CODE_OAUTH_TOKEN`(`claude setup-token` 으로 발급) 또는 `ANTHROPIC_API_KEY`, 로컬은 `claude` 로그인 상태면 된다. 없으면 목록의 명언만 쓴다.
- 그날 명언을 바꾸고 싶으면 그 날짜 파일을 지우고 서버를 다시 시작한다. 모델은 `KITTYSON_QUOTE_MODEL`(기본 `claude-opus-5-5`. 실제로 한 말인지 가려내는 일이라 작은 모델보다 낫다).

## 날씨

`weather` 는 `아이콘 현재기온 ↑최고 ↓최저` 다. 위젯에서 항상 한 줄에 들어오도록 짧게 유지한다. 화면과 위젯은 이 줄을 다음 줄로 넘기지 않고, 폭이 모자라면 글자를 줄인다.

## 모드

웹 화면 오른쪽 아래의 슬라이더로 세 가지 모드를 바꾼다([app.js](src/kittyson/static/app.js)). 글자색과는 별개이고, 모드와 숫자는 그 기기의 브라우저에 저장된다.

| 슬라이더 | 모드 | 모양 |
|---|---|---|
| 왼쪽 | 고양이 + JSON | 기본 |
| 가운데 | 사진 강조 | JSON 글자를 흐리게 |
| 오른쪽 | 숫자 세기 | `"count"` 줄이 붙는다. 한 번 터치 +1, 두 번 터치 −1, 세 번 터치 0으로 |

애플워치 앱은 여기에 타이머를 더한 네 모드를 가진다(아래). 아이폰 위젯에는 모드가 없고 고양이와 JSON만 보여 준다.

## 글자색

글자색은 고정이 아니라 그날 사진을 보고 정한다. 서버가 그날의 고양이를 만들 때 [theme.py](src/kittyson/theme.py) 가 사진 전체의 밝기와 색을 재서(JSON이 사진 전체를 덮기 때문이다) `data/cats/daily/YYYY-MM-DD.json` 에 `theme` 으로 저장한다.

- 밝은 글자와 어두운 글자 중 사진의 더 넓은 부분에서 읽히는 쪽을 고른다.
- 키와 문자열 색의 밝기는 사진의 중간 밝기에 맞추고, 색상은 사진의 주된 색과 겹치지 않게 고른다.
- 글자 뒤 후광은 글자와 부딪히는 부분이 많을수록 진해진다.
- 사진 위에 어두운 막은 깔지 않는다. 고양이는 그대로 두고 글자만 바뀐다.

화면과 위젯은 `/api/today` 의 `cat.theme` 을 받아 그대로 칠한다.

## 아이폰·애플워치

네이티브 앱과 위젯이 `clients/apple/` 에 있다(SwiftUI, WidgetKit). 워치 앱은 워치페이스처럼 켜 두고 쓰는 화면이다. 디지털 크라운으로 모드를 바꾸고 터치로 타이머를 돌리거나 숫자를 센다. 아이폰 홈 화면 위젯은 같은 화면을 보여 주기만 한다. 설치 방법과 워치페이스처럼 쓰는 설정은 [clients/apple/README.md](clients/apple/README.md).

## 배포

다른 프로젝트와 공유하는 게 없는 독립 스택이다([docker-compose.yml](docker-compose.yml)). 컨테이너는 앱 하나이고, 홈서버의 `8787` 포트로 연다. 집 와이파이나 Tailscale 안에서 `http://<홈서버>:8787` 로 접속한다.

`main`에 push하면 다음 순서로 진행된다([.github/workflows/main.yml](.github/workflows/main.yml)).

1. 테스트
2. Docker Hub `:latest` 빌드·푸시
3. Tailscale + SSH로 홈랩 `~/kittyson`에 compose 파일과 `.env`를 쓰고 `docker compose up -d` 실행

배포 시크릿이 하나라도 없으면 2, 3번은 실패하지 않고 건너뛴다.

### 처음 한 번만

**GitHub Secrets**. do-your-english-homework 저장소와 같은 값이다.

- `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
- `TS_OAUTH_CLIENT_ID`, `TS_OAUTH_SECRET`: Tailscale OAuth 클라이언트. `tag:ci` 태그가 필요하다.
- `SERVER_TS_IP`, `SSH_PRIVATE_KEY`: 홈랩의 `deploy` 유저
- `ENV_FILE_CONTENT`: 선택. 서버 `.env`에 넣을 내용(`KITTYSON_PIXABAY_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `KITTYSON_TELEGRAM_TOKEN` 등, [.env.example](.env.example) 참고). 없으면 기본 설정으로 뜨고, 그때는 새 고양이 없이 목록의 명언만 나온다.

**공개 HTTPS 주소가 필요하면** Cloudflare Tunnel을 켠다. 없어도 동작한다.

1. Zero Trust → Networks → Tunnels 에서 터널을 만들고 토큰을 복사한다.
2. 터널의 Route를 추가한다: `<도메인>` → `http://app:8000`
3. `ENV_FILE_CONTENT`에 두 줄을 넣는다.
   ```
   COMPOSE_PROFILES=tunnel
   TUNNEL_TOKEN=...
   ```

### 운영

- 서버에서 직접 다루기: `cd ~/kittyson && docker compose logs -f app` (`restart`, `down`도 같은 폴더에서).
- 로그는 두 곳에 남는다. `docker compose logs`(컨테이너를 다시 만들면 사라짐, 10MB × 3개 상한)와 `~/kittyson/data/logs/app.log`(계속 남음, 5MB × 4개 = 최대 20MB에서 오래된 것부터 지워짐).
- `~/kittyson/data`가 볼륨이다. 날짜별 고양이(`cats/daily`), 날짜별 명언(`quotes`), 로그(`logs`)가 여기에 있다.

설정은 `.env.example` 참고. 계획은 `PLAN.md`. 2026-11-24에 바뀐 것은 [CHANGES.md](CHANGES.md).
