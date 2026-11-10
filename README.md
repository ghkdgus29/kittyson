# kittyson

kitty + JSON. 매일 바뀌는 고양이 배경 위에 위젯 JSON을 생긴 그대로 띄우는 화면.

```json
{
  "meow": "🐱 kittyson v0",
  "now": "2026-11-10T14:01:53+09:00",
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
| `/api/widget` | 위 JSON. `now` 는 요청 순간의 서버 시각 |
| `/cat/today.jpg` | 오늘의 고양이, 1024×1024 |
| `/healthz` | 상태 |

## 고양이 사진

- `data/cats/inbox/` 에 사진을 넣으면 풀에 포함된다. 비어 있으면 cataas.com 에서 하루 1장 받아온다.
- 사진마다 이름·기분을 주고 싶으면 `data/cats/inbox/cats.json`:
  ```json
  [{ "file": "sesame-01.jpg", "name": "참깨", "mood": "sleepy" }]
  ```
- 오늘의 고양이는 `data/cats/daily/YYYY-MM-DD.jpg` 에 확정된다. 바꾸고 싶으면 그 파일과 `.json` 을 지운다.

설정은 `.env.example` 참고. 계획은 `PLAN.md`.
