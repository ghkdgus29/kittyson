# App Store에 올릴 글

App Store Connect의 칸에 그대로 옮겨 적는 초안이다. 스크린샷은 [screenshots/](screenshots/)에 있다.

## 앱 정보

| 칸 | 값 |
|---|---|
| 이름 | kittyson |
| 부제 | 고양이 사진 위의 JSON 시계 |
| 기본 언어 | 한국어 |
| 번들 ID | com.ghkdgus29.kittyson |
| 카테고리 | 유틸리티 (보조: 라이프스타일) |
| 연령 등급 | 4+ |
| 가격 | 무료 |
| 개인정보 처리방침 URL | https://github.com/ghkdgus29/kittyson/blob/main/PRIVACY.md |
| 지원 URL | https://github.com/ghkdgus29/kittyson |

## 프로모션 텍스트

매일 새 고양이, 그리고 그 위에 JSON으로 적힌 오늘의 시간과 날씨와 명언.

## 설명

kittyson은 매일 바뀌는 고양이 사진 위에 시간, 날짜, 요일, 날씨, 오늘의 명언을 JSON으로 보여 주는 앱입니다.

JSON은 개발자가 데이터를 적을 때 쓰는 형식입니다. "weekday": "토요일"처럼 이름과 값을 짝지어 적습니다. kittyson은 오늘 하루를 그 모양 그대로 보여 줍니다.

{
  "time": "09:41:00",
  "date": "2026-11-21",
  "weekday": "토요일",
  "weather": "맑음 12° ↑15 ↓7",
  "quote": "시련은 있어도 실패는 없다"
}

Apple Watch 앱
• 화면 전체가 고양이와 JSON입니다.
• 디지털 크라운을 돌리면 모드가 바뀝니다. JSON, 타이머, 숫자 세기, 사진 보기가 있습니다.
• 타이머: 숫자를 터치하면 시작하고, 끝나면 진동으로 알려 줍니다. 자주 쓰는 시간 네 개는 1분부터 60분까지 바꿀 수 있습니다.
• 숫자 세기: 한 번 터치하면 +1, 두 번 터치하면 −1, 세 번 터치하면 0이 됩니다.
• 컴플리케이션에서 날씨와 명언을 볼 수 있습니다.

iPhone 위젯
• 홈 화면에 오늘의 고양이와 JSON을 올려 둡니다.

알아 두실 것
• 고양이 사진과 명언은 하루에 한 번 바뀝니다.
• 날씨는 서울 기준입니다.
• 계정이 없고 개인정보를 모으지 않습니다.

설명 칸은 이모지를 받지 않는다("invalid characters"). 그래서 날씨 줄의 ☀️ 를 "맑음"으로 적었다.

## 키워드

고양이,JSON,개발자,시계,위젯,타이머,카운터,명언,날씨,워치,코딩,귀여운

## 앱이 수집하는 개인정보 (개인정보 라벨)

"데이터를 수집하지 않음"을 고른다. 앱은 계정, 위치, 광고, 분석 도구가 없다. 서버의 접속 기록에 IP 주소가 남지만 요청에 답하는 데만 쓰고 사용자와 연결하지 않는다.

## 심사 메모 (App Review Information, Notes)

kittyson needs no account or sign-in.

The iPhone app shows today's card (a cat photo with the time, weather and a quote written as JSON) and a short guide. The main features are the iPhone Home Screen widget and the Apple Watch app. On the watch, turn the Digital Crown to switch between four modes: JSON, timer, counter and photo.

The photo and the JSON come from our server at https://kit-son.site, which is public and needs no login. The weather is for Seoul. Cat photos come from Pixabay.

## 스크린샷

| 파일 | 칸 | 크기 |
|---|---|---|
| iphone-1.png, iphone-2.png | iPhone 6.3" (iPhone 17 Pro) | 1206×2622 |
| watch-1-json.png, watch-2-timer.png, watch-3-count.png, watch-4-photo.png | Apple Watch Series 11 (46mm) | 416×496 |
