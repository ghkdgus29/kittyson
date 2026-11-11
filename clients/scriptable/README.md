# kittyson Scriptable 위젯

아이폰 홈 화면에 kittyson 화면을 위젯으로 띄운다. Xcode 없이 [Scriptable](https://scriptable.app) 앱만 있으면 된다.

```
{
  "meow": "🐱 kittyson v1",
  "time": "14:25:28",        ← 초가 흐름
  "date": "2026-11-10",
  "weekday": "화요일",
  "cat": "자몽 · playful",
  "weather": "☀️ 10° 맑음 ↑10 ↓1",
  "fortune": "그루밍은 자기관리다"
}
```

## 설치

폰에는 로더 [kittyson-loader.js](kittyson-loader.js) 만 넣는다. 로더는 실행될 때마다 GitHub `main` 의 최신 [kittyson.js](kittyson.js) 를 받아서 실행한다. 위젯 스크립트를 고쳐서 push하면 폰에서 다시 붙여넣을 필요가 없다.

1. 아이폰에 App Store에서 **Scriptable** 을 설치한다.
2. 아이폰이 서버에 닿을 수 있어야 한다. 셋 중 하나면 된다.
   - 집 와이파이: `http://<홈서버 내부 IP>:8787`. 밖에서는 마지막으로 받은 내용을 보여 준다.
   - Tailscale: 아이폰에 Tailscale 앱을 깔고 같은 계정으로 로그인한다. 어디서든 `http://<홈서버 Tailscale IP>:8787`.
   - Cloudflare Tunnel: 공개 HTTPS 주소. 설정은 루트 [README](../../README.md)의 배포 절.
3. Scriptable에서 `+` 로 새 스크립트를 만들고 [kittyson-loader.js](kittyson-loader.js) 내용을 전부 붙여넣는다. 이름은 `kittyson`.
   - 원본 주소: `https://raw.githubusercontent.com/ghkdgus29/kittyson/main/clients/scriptable/kittyson-loader.js`
4. 맨 위 `SERVER` 를 2번의 주소로 바꾸고 ▶︎ 를 눌러 미리보기를 확인한다.
5. 홈 화면을 길게 눌러 `+` → Scriptable → **Large** 위젯을 추가한다.
6. 위젯을 길게 눌러 "위젯 편집" → Script 를 `kittyson` 으로 고른다.
   - Parameter 칸에 서버 주소를 적으면 `SERVER` 보다 우선한다.

### 수정이 폰에 보이기까지

- **위젯 스크립트**(`clients/scriptable/kittyson.js`): push하면 끝이다. GitHub raw 주소가 최대 5분쯤 예전 내용을 돌려줄 수 있다. 그 뒤 Scriptable 앱에서 ▶︎ 를 누르면 바로 보이고, 홈 화면 위젯은 iOS가 다음에 다시 그릴 때 바뀐다.
- **서버**(JSON 내용, 고양이, 웹 화면): push하면 GitHub Actions가 홈서버에 다시 배포한다. 1~2분 걸린다.
- GitHub에 못 닿으면 로더는 마지막으로 받아 둔 스크립트를 쓴다.

로더 없이 쓰려면 [kittyson.js](kittyson.js) 를 직접 붙여넣고 `DEFAULT_SERVER` 를 바꾼다.

## 크기별 모양

| 위젯 | 내용 |
|---|---|
| Large | 서버 JSON 전체. 목표 크기 |
| Medium | `time`, `date`, `cat`, `weather`, `fortune` |
| Small | `time`, `date`, `cat`, `weather`(아이콘+기온) |
| 잠금화면 직사각형 | `cat`, `weather`, `fortune` 세 줄 (사진 없음) |
| 잠금화면 한 줄 | 날씨 한 줄 |

## 동작 방식

- **초 단위 시계**: 위젯은 몇 분에 한 번만 다시 그려진다. 대신 "오늘 자정부터 흐른 시간" 타이머를 띄우면 iOS가 1초마다 직접 갱신하고, 그 값이 곧 현재 시각이다. `date` 는 다시 그려질 때 기기 시계로 계산한다.
- **글자 크기**: JSON이 위젯 전체를 채운다. 모든 줄이 같은 크기이고, 그 크기는 위젯 높이에 다 들어가는 가장 큰 크기다(Large에서 약 18pt). 위젯 폭보다 긴 값은 띄어쓰기에서 다음 줄로 넘기고 네 칸 들여 쓴다. 키와 값의 첫 단어는 떼지 않고, 넘어간 줄이 `v1",` 처럼 토막만 남으면 글자를 조금 줄여 한 줄에 넣는다. 남는 높이는 줄 사이에 나눠 준다.
- **글자색**: 서버가 오늘 사진을 분석해 정한 색을 `/cat/today.json` 에서 받아 쓴다. 밝은 사진이면 어두운 글자와 밝은 후광, 어두운 사진이면 그 반대다. 받은 색은 저장해 두고 서버에 닿지 못할 때 쓴다.
- **앞자리 0**: iOS 타이머는 `9:05:07`, `5:07` 처럼 앞자리 0을 뺀다. 스크립트가 시각에 맞춰 `0`, `00:`, `00:0` 을 앞에 붙여 보정한다. 보정은 위젯이 다시 그려질 때만 바뀌므로, 새벽 0시대와 1시, 10시 경계에서 잠깐 어긋나 보일 수 있다.
- **갱신**: 15분마다, 그리고 자정과 위 경계 시각 직후에 다시 그려 달라고 요청한다. iOS는 이를 힌트로만 취급한다.
- **오프라인**: 마지막 JSON과 고양이 사진을 캐시해 두고, 서버에 못 닿으면 그걸로 그린다. 시계는 기기 시계로 계속 흐른다.
- **탭**: 위젯을 누르면 서버의 웹 화면이 열린다.

## 조정

- `PAD`: 위젯 크기별 가장자리 여백.
- `MAX_FONT`, `MIN_FONT`: 글자 크기의 범위. `MAX_GAP`: 줄 사이를 최대 얼마나 벌릴지.
- `WIDOW`: 넘어간 줄에 최소 몇 글자가 남아야 하는지.
- `DEFAULT_THEME`: 서버에서 색을 못 받았을 때 쓰는 색.
- `SHADE`: 사진 전체를 어둡게 덮는 정도. 기본은 `0`(사진 그대로)이고, 색만으로 부족하면 `0.2` ~ `0.4`.
- 색을 고르는 규칙 자체는 서버의 `src/kittyson/theme.py` 에 있다.

## 아직 기기에서 확인하지 못한 것

맥에서 Scriptable API를 흉내 낸 환경으로만 검증했다. 실제 아이폰에서 봐야 하는 것:

- 타이머 글자의 폭과 정렬. 어긋나면 `CHAR_W` 를 조정한다.
- 밝은 부분과 어두운 부분이 섞인 사진에서 후광 하나로 충분히 읽히는지. 위젯은 그림자를 한 겹만 쓸 수 있어서 웹 화면보다 약하다.
- `http://` IP 주소로 요청이 되는지. 안 되면 HTTPS 주소(Cloudflare Tunnel)가 필요하다.
- 로더가 내려받은 스크립트를 실행하는 부분.
- 잠금화면 위젯에서의 글자 크기.
