# kittyson

kitty + JSON. 매일 바뀌는 고양이 배경 위에 위젯 JSON을 생긴 그대로 띄우는 화면.

```json
{
  "meow": "🐱 kittyson v1",
  "time": "14:01:53",
  "date": "2026-11-10",
  "weekday": "화요일",
  "cat": "참깨 · sleepy",
  "weather": "☁️ 11° 흐림 ↑14 ↓6",
  "fortune": "낮잠은 생산성이다"
}
```

## 실행

```sh
uv sync
uv run kittyson          # http://localhost:8000
uv run pytest
```

| 경로 | 설명 |
|---|---|
| `/` | 화면 (정사각형 카드) |
| `/api/widget` | 위 JSON. `time`, `date` 는 요청 순간의 서버 시각(24시간제) |
| `/cat/today.jpg` | 오늘의 고양이, 1024×1024 |
| `/cat/today.json` | 오늘의 고양이 이름·기분과, 그 사진 위에서 잘 읽히는 글자색(`theme`) |
| `/healthz` | 상태 |

## 고양이 사진

- `data/cats/inbox/` 에 사진을 넣으면 풀에 포함된다. 비어 있으면 cataas.com 에서 하루 1장 받아온다.
- 사진마다 이름·기분을 주고 싶으면 `data/cats/inbox/cats.json`:
  ```json
  [{ "file": "sesame-01.jpg", "name": "참깨", "mood": "sleepy" }]
  ```
- 오늘의 고양이는 `data/cats/daily/YYYY-MM-DD.jpg` 에 확정된다. 바꾸고 싶으면 그 파일과 `.json` 을 지운다.

## 한 마디

`fortune` 은 Claude가 하루에 한 번 쓴다([fortune.py](src/kittyson/fortune.py), Claude Agent SDK). 날짜·요일·날씨·오늘의 고양이와 최근 2주 문장을 넘겨서, 그날에 어울리고 전과 겹치지 않는 한 줄을 받는다.

- 그날 첫 요청 때 백그라운드로 만들어 `data/fortunes/YYYY-MM-DD.json` 에 확정한다. 만들어지기 전 몇 초 동안과, Claude를 못 부르는 날에는 기존 문장 목록에서 날짜로 고른 한 줄이 나온다.
- 인증은 `claude` CLI와 같다. 서버는 `.env` 의 `CLAUDE_CODE_OAUTH_TOKEN`(`claude setup-token` 으로 발급) 또는 `ANTHROPIC_API_KEY`, 로컬은 `claude` 로그인 상태면 된다. 없으면 목록 문장만 쓴다.
- 실패하면 30분 뒤 다시 시도하고, 하루 3번까지만 한다. 위젯 두 줄을 넘는 문장(22자 초과)은 버린다.
- 오늘 문장을 바꾸고 싶으면 그 날짜 파일을 지운다. 모델은 `KITTYSON_FORTUNE_MODEL`(기본 `haiku`).

## 글자색

글자색은 고정이 아니라 그날 사진을 보고 정한다. 서버가 오늘의 고양이를 확정할 때 [theme.py](src/kittyson/theme.py) 가 사진 전체의 밝기와 색을 재서(JSON이 사진 전체를 덮기 때문이다) `data/cats/daily/YYYY-MM-DD.json` 에 `theme` 으로 저장한다.

- 밝은 글자와 어두운 글자 중 사진의 더 넓은 부분에서 읽히는 쪽을 고른다.
- 키와 문자열 색의 밝기는 사진의 중간 밝기에 맞추고, 색상은 사진의 주된 색과 겹치지 않게 고른다.
- 글자 뒤 후광은 글자와 부딪히는 부분이 많을수록 진해진다.
- 사진 위에 어두운 막은 깔지 않는다. 고양이는 그대로 두고 글자만 바뀐다.

화면과 위젯은 `/cat/today.json` 의 `theme` 을 받아 그대로 칠한다.

## 아이폰 위젯

Scriptable 앱용 위젯 스크립트가 `clients/scriptable/` 에 있다. 설치 방법은 [clients/scriptable/README.md](clients/scriptable/README.md).

폰에는 로더(`kittyson-loader.js`)만 한 번 붙여넣는다. 로더가 실행될 때마다 GitHub에서 최신 `kittyson.js` 를 받아 오므로, 위젯 스크립트 수정은 push만 하면 폰에 반영된다.

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
- `~/kittyson/data`가 볼륨이다. 오늘의 고양이 캐시(`cats/daily`), 직접 넣는 사진(`cats/inbox`), 날짜별 한 마디(`fortunes`)가 여기에 있다.

설정은 `.env.example` 참고. 계획은 `PLAN.md`.
