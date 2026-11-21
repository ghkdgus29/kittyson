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
                        Text(note).foregroundStyle(.secondary)
                    }
                    if !topic.rows.isEmpty {
                        Grid(alignment: .leadingFirstTextBaseline, horizontalSpacing: 14, verticalSpacing: 10) {
                            ForEach(topic.rows, id: \.mark) { row in
                                GridRow {
                                    Text(row.mark).font(.system(.callout, design: .monospaced).weight(.semibold))
                                        .foregroundStyle(Color(hex: "#f2c14e"))
                                    Text(row.text)
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
        var note: LocalizedStringKey?
        var rows: [(mark: String, text: LocalizedStringKey)] = []
    }

    private static let topics = [
        Topic(title: "kittyson",
              note: "매일 바뀌는 고양이 사진 위에 시간, 날씨, 오늘의 명언을 JSON으로 보여 줍니다. 이 앱은 워치 앱과 위젯을 담고 있고, 열면 고양이와 JSON을 새로 받아 옵니다. "),
        Topic(title: "워치 페이스처럼 쓰기",
              note: "watchOS는 앱이 워치 페이스가 되는 것을 허용하지 않습니다. 대신 kittyson을 계속 앞에 둡니다.",
              rows: [
                ("1", "워치의 **설정 → 일반 → 시계 화면으로 돌아가기 → kittyson → 사용자화**에서 **1시간 후**를 고릅니다."),
                ("2", "워치에서 kittyson을 엽니다. 이제 손목을 들면 시계 대신 kittyson이 보입니다."),
                ("3", "1시간 넘게 보지 않으면 원래 페이스로 돌아갑니다. 그 페이스에 kittyson 컴플리케이션을 올려 두면 한 번 눌러 돌아옵니다."),
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
                ("터치", "숫자를 터치하면 그 시간으로 시작합니다. 처음에는 1, 5, 15, 30분입니다."),
                ("길게", "숫자를 길게 누르면 크라운으로 1분부터 60분까지 바꿉니다. 터치하면 시작합니다."),
                ("취소", "타이머가 도는 중에 두 번 터치합니다."),
                ("끝", "진동이 옵니다. 한 번 터치하면 멈춥니다."),
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
              note: "홈 화면을 길게 눌러 **편집 → 위젯 추가 → kittyson**을 고릅니다. 고양이와 JSON 보여 주기 기능만 지원합니다."),
    ]
}
