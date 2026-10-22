pragma ComponentBehavior: Bound
import QtQuick

Item {
    id: clock
    property string timeText: '00:00'
    property string secondsText: '00'
    property string dateText: ''
    property color accent: '#ae96ef'
    property color ink: '#f3dfcf'
    property color muted: '#a49aae'
    property real unit: 1
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top; anchors.topMargin: -3 * clock.unit
        spacing: 9 * clock.unit
        Text {
            text: clock.timeText
            color: clock.ink
            font.family: 'Adwaita Sans'
            font.pixelSize: 64 * clock.unit
            font.weight: Font.Light
            font.features: {'tnum': 1}
            font.letterSpacing: -3 * clock.unit
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 5 * clock.unit
            Text { text: clock.secondsText; color: clock.accent; font.family: 'Adwaita Sans'; font.pixelSize: 24 * clock.unit; font.features: {'tnum': 1} }
            Text { text: 'SEG'; color: clock.muted; font.pixelSize: 8 * clock.unit; font.letterSpacing: 2 * clock.unit }
        }
    }
    Column {
        anchors.bottom: parent.bottom; anchors.bottomMargin: 1 * clock.unit
        width: parent.width
        spacing: 12 * clock.unit
        Text {
            text: clock.dateText; color: clock.muted
            width: parent.width; horizontalAlignment: Text.AlignHCenter
            font.pixelSize: 10 * clock.unit; font.letterSpacing: 0.7 * clock.unit
            elide: Text.ElideRight
        }
        Rectangle {
            width: parent.width; height: 4 * clock.unit; radius: height / 2
            color: Qt.rgba(clock.accent.r,clock.accent.g,clock.accent.b,0.12)
            Rectangle {
                width: parent.width * Math.min(1, Math.max(0, Number(clock.secondsText) / 59))
                height: parent.height; radius: height / 2; color: clock.accent
                Behavior on width { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
            }
        }
    }
}
