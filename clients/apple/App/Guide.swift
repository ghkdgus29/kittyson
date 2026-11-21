import SwiftUI

/// What kittyson is and how to use it. Mostly the watch app, since that is where it is used.
/// The same facts as this folder's README.md, in fewer words.
struct Guide: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 36) {
            ForEach(Guide.topics, id: \.title) { topic in
                VStack(alignment: .leading, spacing: 12) {
                    Text(topic.title).font(.title3.bold())
                    if let note = topic.note {
                        Text(Guide.glued(note)).foregroundStyle(.secondary)
                    }
                    if !topic.rows.isEmpty {
                        Grid(alignment: .leadingFirstTextBaseline, horizontalSpacing: 14, verticalSpacing: 10) {
                            ForEach(topic.rows, id: \.mark) { row in
                                GridRow {
                                    Text(row.mark).font(.system(.callout, design: .monospaced).weight(.semibold))
                                        .foregroundStyle(Color(hex: "#f2c14e"))
                                    Text(Guide.glued(row.text))
                                }
                            }
                        }
                    }
                }
            }
        }
        .font(.callout)
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private struct Topic {
        var title: String
        var note: String?
        var rows: [(mark: String, text: String)] = []
    }

    /// Keeps a particle on the line of its word. Without this a line can end between Latin letters or
    /// digits and the Korean that follows, as in "kittyson" + "을" or "60" + "분".
    private static func glued(_ text: String) -> LocalizedStringKey {
        LocalizedStringKey(text.replacing(#/([0-9A-Za-z]\**)(?=[가-힣])/#) { "\($0.1)\u{2060}" })
    }

    // "\n" starts a new line. One sentence to a line, and a long sentence broken where it pauses.
    private static let topics = [
        Topic(title: "kittyson",
              note: "매일 바뀌는 고양이 사진 위에 시간, 날씨, 오늘의 명언을 JSON으로 보여 줍니다.\n이 앱은 워치 앱과 아이폰 위젯 두 가지를 지원합니다.\n워치 앱은 계속 앞에 두고 쓰고, 아이폰 위젯은 홈 화면에 올려 고양이와 JSON을 보여 줍니다."),
        Topic(title: "워치에서 계속 앞에 두기",
              note: "손목을 들 때마다 kittyson이 보이도록 워치 설정을 바꿉니다.",
              rows: [
                ("1", "워치의 **설정 → 일반 → 시계 화면으로 돌아가기 → kittyson → 사용자화**에서 **1시간 후**를 고릅니다."),
                ("2", "워치에서 kittyson을 엽니다.\n이제 손목을 들면 kittyson이 보입니다."),
                ("3", "1시간 넘게 보지 않으면 시계 화면으로 돌아갑니다."),
              ]),
        Topic(title: "디지털 크라운",
              note: "돌리면 모드가 바뀝니다.",
              rows: [
                ("json", "시간, 날짜, 요일, 날씨, 명언"),
                ("timer", "타이머"),
                ("count", "숫자 세기"),
                ("photo", "고양이 사진 자세히 보기"),
              ]),
        Topic(title: "타이머 모드",
              rows: [ 
                ("터치", "숫자를 터치하면 그 시간으로 시작합니다.\n처음에는 1, 5, 15, 30분입니다."),
                ("길게", "숫자를 길게 누르면 크라운으로 1분부터 60분까지 바꿉니다.\n터치하면 시작합니다."),
                ("취소", "타이머가 도는 중에 두 번 터치합니다."),
                ("끝", "진동이 옵니다.\n한 번 터치하면 멈춥니다."),
                ("알람", "아이폰의 **Watch 앱 → 일반 → 백그라운드 앱 새로 고침**에서 kittyson이 켜져 있어야 울립니다."),
              ]),
        Topic(title: "카운터 모드",
              rows: [
                ("+1", "한 번 터치"),
                ("−1", "두 번 터치"),
                ("0", "세 번 터치"),
              ]),
        Topic(title: "워치의 짧은 키",
              note: "화면이 좁아 키를 줄여 씁니다.",
              rows: [
                ("t", "time, 시간"),
                ("d", "date, 날짜"),
                ("wd", "weekday, 요일"),
                ("wx", "weather, 날씨"),
                ("q", "quote, 명언"),
                ("n", "count, 숫자 세기"),
                ("tm", "timer, 타이머"),
              ]),
        Topic(title: "아이폰 위젯",
              note: "홈 화면을 길게 눌러 **편집 → 위젯 추가 → kittyson**을 고릅니다.\n고양이와 JSON 보여 주기 기능만 지원합니다."),
        Topic(title: "고양이 사진",
              note: "사진은 [Pixabay](https://pixabay.com)에서 가져옵니다."),
        Topic(title: "개인정보",
              note: "kittyson은 계정이 없고 개인정보를 모으지 않습니다.\n[개인정보 처리방침](https://github.com/ghkdgus29/kittyson/blob/main/PRIVACY.md)"),
    ]
}
