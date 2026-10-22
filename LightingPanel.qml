pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: lights
    property string endpoint
    property var lightingInfo: ({})
    property color accent: '#ae96ef'
    property color ink: '#f3dfcf'
    property color muted: '#a49aae'
    property real unit: 1
    property string selectedMode: 'Fijo'
    property string selectedTarget: 'Ambos'
    property color previewColor: '#00ff00'
    property real selectedSpeed: 50
    property bool initialized: false
    onLightingInfoChanged: {
        if(!initialized && lightingInfo.mode) {
            selectedMode=lightingInfo.mode; selectedTarget=lightingInfo.target || 'Ambos';
            previewColor='#'+(lightingInfo.color || '00FF00'); selectedSpeed=lightingInfo.speed===undefined ? 50 : lightingInfo.speed;
            initialized=true;
        }
    }
    property bool saving: false
    property string message: ''
    spacing: 8*unit
    function applyLights() {
        if(saving)return;
        saving=true;message='Aplicando…';
        let request=new XMLHttpRequest();request.open('POST',endpoint+'/lighting');request.setRequestHeader('Content-Type','application/json');
        request.onreadystatechange=function() {
            if(request.readyState!==XMLHttpRequest.DONE)return;
            saving=false;
            message=request.status===200 ? 'Aplicado · '+lights.selectedMode+' · '+Math.round(lights.selectedSpeed)+'%' : 'No se pudo aplicar. Revisa OpenRGB.';
        };
        request.send(JSON.stringify({mode:selectedMode,target:selectedTarget,color:previewColor.toString().substring(1),speed:Math.round(lights.selectedSpeed)}));
    }
    RowLayout {
        Layout.fillWidth: true
        Text { text: 'SINCRONIZAR'; color: lights.muted; font.pixelSize: 10*lights.unit }
        ComboBox {
            id: destination; Layout.fillWidth: true; model: ['Todo','Ambos','Placa','RAM','HyperX']
            currentIndex: model.indexOf(lights.selectedTarget)
            onActivated: lights.selectedTarget=currentText
            font.pixelSize: 12*lights.unit
            contentItem: Text { text: destination.currentText; color: lights.ink; leftPadding: 10*lights.unit; verticalAlignment: Text.AlignVCenter; font.pixelSize: 12*lights.unit }
            background: Rectangle { radius: 8*lights.unit; color: Qt.rgba(lights.accent.r,lights.accent.g,lights.accent.b,0.08); border.color: Qt.rgba(lights.accent.r,lights.accent.g,lights.accent.b,0.18) }
            Layout.preferredHeight: 30*lights.unit
        }
    }
    RowLayout {
        Layout.fillWidth: true; spacing: 4*lights.unit
        Repeater {
            model: ['Fijo','Respiración','Arcoíris','Apagado']
            Button {
                id: mode; required property string modelData
                text: modelData; Layout.fillWidth: true; Layout.preferredWidth: 1; Layout.preferredHeight: 28*lights.unit
                onClicked: {lights.selectedMode=modelData;lights.message='Vista previa · pulsa Aplicar para enviarlo al equipo'}
                contentItem: Text { text: mode.text; color: lights.selectedMode===mode.modelData ? '#101217' : lights.ink; font.pixelSize: 11*lights.unit; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { radius: 8*lights.unit; color: lights.selectedMode===mode.modelData ? lights.accent : Qt.rgba(lights.accent.r,lights.accent.g,lights.accent.b,0.08) }
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true; spacing: 8*lights.unit
        Repeater {
            model: ['#f05260','#edac70','#00ff00','#2080ff','#ae96ef','#ffffff']
            Rectangle {
                required property string modelData
                width: 23*lights.unit; height: width; radius: width/2; color: modelData
                border.width: lights.previewColor.toString()===modelData ? 2 : 0; border.color: lights.ink
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: {lights.previewColor=parent.modelData;hex.text=parent.modelData} }
            }
        }
        TextField {
            color: lights.ink; selectionColor: lights.accent
            background: Rectangle { radius: 8*lights.unit; color: Qt.rgba(lights.accent.r,lights.accent.g,lights.accent.b,0.06); border.color: Qt.rgba(lights.accent.r,lights.accent.g,lights.accent.b,0.18) }
            id: hex; Layout.fillWidth: true; Layout.preferredHeight: 28*lights.unit
            text: lights.previewColor.toString(); font.pixelSize: 11*lights.unit; maximumLength: 7
            validator: RegularExpressionValidator { regularExpression: /#[0-9a-fA-F]{6}/ }
            onEditingFinished: if(acceptableInput) lights.previewColor=text
        }
    }
    RowLayout {
        Layout.fillWidth: true
        Text { text: 'VELOCIDAD '+Math.round(lights.selectedSpeed)+'%'; color: lights.muted; font.pixelSize: 10*lights.unit }
        Slider { id: speed; objectName: 'lightingSpeed'; Layout.fillWidth: true; from: 0; to: 100; value: lights.selectedSpeed; stepSize: 1; onMoved: {lights.selectedSpeed=value;lights.message='Vista previa · pulsa Aplicar para cambiar el equipo'} enabled: lights.selectedMode==='Respiración' || lights.selectedMode==='Arcoíris'; Layout.preferredHeight: 28*lights.unit
            background: Rectangle { x: speed.leftPadding; y: speed.topPadding+speed.availableHeight/2-height/2; width: speed.availableWidth; height: 4*lights.unit; radius: height/2; color: Qt.rgba(lights.accent.r,lights.accent.g,lights.accent.b,0.12)
                Rectangle { width: speed.visualPosition*parent.width; height: parent.height; radius: height/2; color: lights.accent; opacity: speed.enabled ? 1 : 0.25 }
            }
            handle: Rectangle { x: speed.leftPadding+speed.visualPosition*(speed.availableWidth-width); y: speed.topPadding+speed.availableHeight/2-height/2; width: 16*lights.unit; height: width; radius: width/2; color: speed.pressed ? lights.ink : lights.accent; opacity: speed.enabled ? 1 : 0.25 }
        }
        Button {
            id: applyButton
            contentItem: Text { text: applyButton.text; color: lights.ink; font.pixelSize: 12*lights.unit; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            background: Rectangle { radius: 8*lights.unit; color: Qt.rgba(lights.accent.r,lights.accent.g,lights.accent.b,0.16); border.color: lights.accent }
            text: lights.saving ? 'Aplicando…' : 'Aplicar'; enabled: !lights.saving
            Layout.preferredHeight: 30*lights.unit; font.pixelSize: 12*lights.unit
            onClicked: lights.applyLights()
        }
    }
    Text { text: lights.message || 'Todo: placa + RAM + HyperX · Ambos: placa + RAM'; color: lights.muted; font.pixelSize: 10*lights.unit; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    Item { Layout.fillHeight: true }
}
