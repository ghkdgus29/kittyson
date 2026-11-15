# kittyson: 아이폰·애플워치

네이티브 클라이언트. 한 프로젝트에 네 개가 들어 있다.

| 타깃 | 무엇 |
|---|---|
| `KittysonWatch` | 애플워치 앱. 워치페이스처럼 쓰는 화면이고, 모드와 숫자 세기는 여기에만 있다 |
| `KittysonWatchWidget` | 워치 컴플리케이션·스마트 스택 위젯. 누르면 워치 앱이 열린다 |
| `KittysonWidget` | 아이폰 홈 화면 위젯 (Large). 고양이와 JSON을 보여 주기만 한다 |
| `Kittyson` | 아이폰 앱. 위젯과 워치 앱을 담는 그릇이고, 같은 카드를 보여 준다 |

## 워치 앱

화면 전체가 고양이와 JSON이다. 시스템 시계는 숨겼다.

- **디지털 크라운**으로 모드를 바꾼다: 고양이 + JSON, 사진 강조(글자 흐리게), 숫자 세기.
- **숫자 세기**에서는 `"time"` 과 `"count"` 두 줄만 크게 나온다. 한 번 터치 +1, 두 번 터치 −1, 세 번 터치 0으로. 터치마다 진동이 온다.
- 손목을 내려 화면이 어두워지면 `"time"` 은 초 없이 시:분만 나온다.

### 워치페이스처럼 쓰기

watchOS는 다른 앱이 워치페이스가 되는 것을 허용하지 않는다. 대신 앱을 계속 앞에 둔다.

1. 워치의 설정 → 일반 → 시계 화면으로 돌아가기 → kittyson → 사용자화 → **1시간 후**.
2. kittyson 앱을 연다. 이후 손목을 들면 시계 대신 kittyson이 보인다. 한 시간에 한 번이라도 보면 계속 유지된다.
3. 1시간 넘게 안 보면(잘 때, 벗어 뒀을 때) 애플 페이스로 돌아간다. 그 페이스에 kittyson 컴플리케이션을 올려 두고 한 번 누르면 돌아온다.

컴플리케이션은 네 가지 모양이 있어서 어느 페이스에나 올라간다: 원형·모서리(고양이 아이콘), 한 줄(고양이 + 날씨), 직사각형(날씨와 명언).

## 설치

Xcode 26, iOS 17 이상, watchOS 11 이상.

1. `Config/Local.example.xcconfig` 를 `Config/Local.xcconfig` 로 복사하고 서버 주소(`KITTYSON_HOST`)와 팀 ID(`DEVELOPMENT_TEAM`)를 적는다. 이 파일은 git에 올라가지 않는다.
2. `Kittyson.xcodeproj` 를 열고, 위쪽에서 `Kittyson` 스킴과 자기 아이폰을 골라 실행(⌘R)한다. 워치 앱은 아이폰 앱 안에 들어 있어서 같이 설치된다. 워치에 안 보이면 아이폰의 Watch 앱 → 사용 가능한 앱에서 설치한다.
3. 아이폰: 홈 화면을 길게 눌러 편집 → 위젯 추가 → kittyson. 워치: 페이스를 길게 눌러 편집 → 컴플리케이션에서 kittyson을 고른다.

- 무료 Apple 계정이면 7일마다 다시 실행(⌘R)해서 설치해야 한다.
- 서버 주소는 빌드할 때 앱에 들어간다. 주소를 바꾸면 다시 빌드한다.
- 서버가 HTTP여도 되도록 ATS를 풀어 두었다.

## 구조

```
project.yml      Xcode 프로젝트의 원본. 타깃을 고치면 `xcodegen generate` (brew install xcodegen)
Config/          서버 주소(xcconfig), 생성되는 Info.plist·entitlements
Shared/          네 타깃이 같이 쓰는 코드
  Layout.swift     JSON을 칸에 맞추기: 들어가는 가장 큰 글자 크기와 줄바꿈 (웹 화면과 같은 규칙)
  Counter.swift    숫자 세기 규칙 (워치 앱)
  Store.swift      모드와 숫자 저장 (워치 앱)
  Server.swift     서버에서 받아 오기, 마지막 응답을 디스크에 보관
  JsonText.swift   JSON 그리기. "time" 은 시스템 타이머 글자라 위젯에서도 초가 흐른다
  Card.swift       사진 + JSON
  Timeline.swift   위젯 갱신 (30분마다 서버 확인)
App/ Widget/ WatchApp/ WatchWidget/   타깃마다 화면 하나씩
Tests/main.swift   Layout·Counter 점검
```

점검:

```sh
swiftc Shared/Counter.swift Shared/Layout.swift Tests/main.swift -o /tmp/kittyson-check && /tmp/kittyson-check
```

시뮬레이터로 로컬 서버를 볼 때:

```sh
xcodebuild -project Kittyson.xcodeproj -scheme Kittyson \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' KITTYSON_HOST=127.0.0.1:8000 build
```
