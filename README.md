# kittyson

kitty + JSON. 매일 바뀌는 고양이 배경 위에 위젯 JSON을 생긴 그대로 띄우는 화면.

```json
{
  "time": "14:01:53",
  "date": "2026-11-10",
  "weekday": "화요일",
  "weather": "☁️ 11° ↑14 ↓6",
  "quote": "천 리 길도 한 걸음부터 시작된다"
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
| `/api/widget` | 위 JSON. `time`, `date` 는 요청 순간의 서버 시각(24시간제) |
| `/cat/today.jpg` | 오늘의 고양이, 1024×1024 |
| `/cat/today.json` | 오늘 사진의 출처와, 그 사진 위에서 잘 읽히는 글자색(`theme`) |
| `/healthz` | 상태 |

## 고양이 사진

- `data/cats/inbox/` 에 사진을 넣으면 풀에 포함된다. 비어 있으면 cataas.com 에서 하루 1장 받아온다.
- 오늘의 고양이는 `data/cats/daily/YYYY-MM-DD.jpg` 에 확정된다. 바꾸고 싶으면 그 파일과 `.json` 을 지운다.
- 사진에서 읽어낸 글자색은 옆의 `.json` 에 버전(`v`)과 함께 저장한다. 분석 방식을 바꾸면 [base.py](src/kittyson/cats/base.py)의 `VERSION` 을 올린다. 버전이 다른 `.json` 은 캐시로 치지 않아서, 사진은 그대로 두고 다시 읽어낸다.

## 오늘의 명언

`quote` 는 실제 인물이 남긴 동기부여 명언 한 줄이다. Claude가 하루에 한 번 고른다([quote.py](src/kittyson/quote.py), Claude Agent SDK). 날짜·요일, 그날 찾아볼 분야(철학자, 운동선수, 한국 인물 등)와 최근 두 달의 명언을 넘겨서, 전과 겹치지 않는 한 줄을 받는다.

- 화면에는 문장만 나온다. 누가 한 말인지는 `data/quotes/YYYY-MM-DD.json` 의 `by` 에 남는다.
- Claude가 고른 명언은 따로 검증하지 않는다. 출처가 분명한 말만 고르라고 시키지만, 틀릴 수 있다. 의심스러우면 `by` 를 보고 확인한다.
- 그날 첫 요청 때 백그라운드로 골라 날짜 파일에 확정한다. 고르기 전 몇 초 동안과, Claude를 못 부르는 날에는 출처를 확인해 둔 명언 목록(`QUOTES`, 줄마다 말한 사람과 출처가 적혀 있다)에서 날짜로 고른 한 줄이 나온다.
- 인증은 `claude` CLI와 같다. 서버는 `.env` 의 `CLAUDE_CODE_OAUTH_TOKEN`(`claude setup-token` 으로 발급) 또는 `ANTHROPIC_API_KEY`, 로컬은 `claude` 로그인 상태면 된다. 없으면 목록의 명언만 쓴다.
- 실패하면 30분 뒤 다시 시도하고, 하루 3번까지만 한다. 28자 이내인 명언을 부탁하고, 40자를 넘는 문장은 버린다.
- 오늘 명언을 바꾸고 싶으면 그 날짜 파일을 지운다. 모델은 `KITTYSON_QUOTE_MODEL`(기본 `opus`. 실제로 한 말인지 가려내는 일이라 작은 모델보다 낫다).

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

글자색은 고정이 아니라 그날 사진을 보고 정한다. 서버가 오늘의 고양이를 확정할 때 [theme.py](src/kittyson/theme.py) 가 사진 전체의 밝기와 색을 재서(JSON이 사진 전체를 덮기 때문이다) `data/cats/daily/YYYY-MM-DD.json` 에 `theme` 으로 저장한다.

- 밝은 글자와 어두운 글자 중 사진의 더 넓은 부분에서 읽히는 쪽을 고른다.
- 키와 문자열 색의 밝기는 사진의 중간 밝기에 맞추고, 색상은 사진의 주된 색과 겹치지 않게 고른다.
- 글자 뒤 후광은 글자와 부딪히는 부분이 많을수록 진해진다.
- 사진 위에 어두운 막은 깔지 않는다. 고양이는 그대로 두고 글자만 바뀐다.

화면과 위젯은 `/cat/today.json` 의 `theme` 을 받아 그대로 칠한다.

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
- `ENV_FILE_CONTENT`: 선택. 서버 `.env`에 넣을 내용(`CLAUDE_CODE_OAUTH_TOKEN`, `KITTYSON_LAT` 등, [.env.example](.env.example) 참고). 없으면 기본 설정으로 뜬다.

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
- `~/kittyson/data`가 볼륨이다. 오늘의 고양이 캐시(`cats/daily`), 직접 넣는 사진(`cats/inbox`), 날짜별 명언(`quotes`)이 여기에 있다.

설정은 `.env.example` 참고. 계획은 `PLAN.md`. 코드를 읽는 순서는 [READING.md](READING.md).
