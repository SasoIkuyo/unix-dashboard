pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: panel
    property bool lightingView: true
    property var lightingInfo: ({})
    property var fanInfo: ({})
    property var preferences: ({})
    property string endpoint
    property color accent: '#ae96ef'
    property color ink: '#f3dfcf'
    property color muted: '#a49aae'
    property real unit: 1
    property bool saving: false
    property string message: ''
    property var rows: (fanInfo.rows || []).filter(r=>r.rpm>0 || r.source==='NVIDIA')
    property real cpuRpm: {let cpu=rows.find(r=>r.source==='Placa');return cpu && cpu.rpm!==null ? cpu.rpm : 0}
    property real gpuRpm: {let gpu=rows.filter(r=>r.source==='NVIDIA' && r.rpm!==null);return gpu.length ? gpu.reduce((sum,r)=>sum+r.rpm,0)/gpu.length : 0}
    signal saved(var values)
    signal editTargets()
    function changeMode(mode) {
        if(saving || (mode===preferences.fanMode && !preferences.fanBoost))return;
        if(mode!=='Automático' && !(preferences.fanChannels || []).length && !preferences.fanGPU) {message='Elige primero los ventiladores en Ajustes.';editTargets();return}
        saving=true;message='';
        let req=new XMLHttpRequest();req.open('POST',endpoint+'/settings');req.setRequestHeader('Content-Type','application/json');
        req.onreadystatechange=function() {if(req.readyState!==XMLHttpRequest.DONE)return;saving=false;if(req.status===200)panel.saved(JSON.parse(req.responseText));else message='No se pudo aplicar el modo. Revisa el servicio en Ajustes.'};
        req.send(JSON.stringify(mode==='Máximo' ? {fanBoost:true} : {fanMode:mode,fanBoost:false}));
    }
    Button {
        id: lightingToggle
        objectName: 'toggleLighting'
        anchors.right: parent.right; anchors.top: parent.top; anchors.topMargin: -37*panel.unit
        height: 28*panel.unit
        text: panel.lightingView ? '◌  Refrigeración' : '✦  Iluminación'
        onClicked: panel.lightingView=!panel.lightingView
        contentItem: Text { text: lightingToggle.text; color: panel.accent; font.pixelSize: 11*panel.unit; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { radius: 10*panel.unit; color: Qt.rgba(panel.accent.r,panel.accent.g,panel.accent.b,0.1); border.color: Qt.rgba(panel.accent.r,panel.accent.g,panel.accent.b,0.2) }
    }
    RowLayout {
        anchors.fill: parent; anchors.topMargin: 22*panel.unit; spacing: 24*panel.unit
        ColumnLayout {
            Layout.preferredWidth: 365*panel.unit; Layout.fillHeight: true; spacing: 3*panel.unit
            PcCooling { Layout.fillWidth: true; Layout.fillHeight: true; accent: lightingControls.previewColor; lightingMode: lightingControls.selectedMode; lightingSpeed: lightingControls.selectedSpeed; lightingTarget: lightingControls.selectedTarget; ink: panel.ink; muted: panel.muted; cpuRpm: panel.cpuRpm; gpuRpm: panel.gpuRpm; animate: panel.visible }
            Text { text: '6 ventiladores del hub · sin RPM disponibles'; color: panel.muted; font.pixelSize: 9*panel.unit; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
        }
        LightingPanel {
            id: lightingControls
            visible: panel.lightingView
            Layout.fillWidth: true; Layout.fillHeight: true
            endpoint: panel.endpoint; lightingInfo: panel.lightingInfo
            accent: panel.accent; ink: panel.ink; muted: panel.muted; unit: panel.unit
        }
        ColumnLayout {
            visible: !panel.lightingView
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 9*panel.unit
            RowLayout { Layout.fillWidth: true
                Text { text: 'TU EQUIPO'; color: panel.accent; font.pixelSize: 12*panel.unit; font.bold: true; Layout.fillWidth: true }
                Button { text: 'Curvas y dispositivos'; flat: true; onClicked: panel.editTargets(); font.pixelSize: 10*panel.unit }
            }
            Repeater { model: panel.rows.length
                RowLayout { id: rpmRow; required property int index; property var reading: panel.rows[index]; Layout.fillWidth: true
                    Text { text: rpmRow.reading.source==='Placa' ? 'ARCTIC · CPU_FAN1' : rpmRow.reading.label; color: panel.muted; font.pixelSize: 12*panel.unit; Layout.fillWidth: true }
                    Text { text: rpmRow.reading.rpm!==null ? rpmRow.reading.rpm+' RPM' : rpmRow.reading.percent+'%'; color: panel.ink; font.pixelSize: 17*panel.unit; font.bold: true; Layout.preferredWidth: 105*panel.unit; horizontalAlignment: Text.AlignRight }
                }
            }
            Text { text: 'MODO DE USO'; color: panel.accent; font.pixelSize: 10*panel.unit; Layout.topMargin: 6*panel.unit }
            RowLayout { Layout.fillWidth: true; spacing: 5*panel.unit
                Repeater { model: ['Automático','Silencioso','Equilibrado','Rendimiento']
                    Button { id: modeButton; required property string modelData; objectName: 'mode'+modelData; text: modelData; Layout.fillWidth: true; Layout.preferredWidth: 1; enabled: !panel.saving && (panel.fanInfo.controlReady || modelData==='Automático'); onClicked: panel.changeMode(modelData)
                        contentItem: Text { text: modeButton.text; font.pixelSize: 10*panel.unit; color: !panel.preferences.fanBoost && panel.preferences.fanMode===modeButton.modelData ? '#101217' : panel.ink; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                        background: Rectangle { radius: 9*panel.unit; color: !panel.preferences.fanBoost && panel.preferences.fanMode===modeButton.modelData ? panel.accent : Qt.rgba(panel.accent.r,panel.accent.g,panel.accent.b,0.09); border.color: Qt.rgba(panel.accent.r,panel.accent.g,panel.accent.b,0.18) }
                    }
                }
            }
            Button {
                id: maximumButton; objectName: 'modeMáximo'; text: panel.preferences.fanBoost ? 'Máximo · 100 % activo' : 'Máximo · 100 %'
                Layout.fillWidth: true; enabled: !panel.saving && !!panel.fanInfo.controlReady
                onClicked: panel.changeMode('Máximo')
                contentItem: Text { text: maximumButton.text; font.pixelSize: 11*panel.unit; color: panel.preferences.fanBoost ? '#101217' : panel.accent; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { radius: 9*panel.unit; color: panel.preferences.fanBoost ? panel.accent : Qt.rgba(panel.accent.r,panel.accent.g,panel.accent.b,0.08); border.color: panel.accent; border.width: 1 }
            }
            Text {
                text: 'Control CPU '+((((panel.fanInfo.control || {}).targets || {})['2']) ? ((panel.fanInfo.control || {}).targets['2']+'%') : 'automático')+' · GPU '+((((panel.fanInfo.control || {}).targets || {}).gpu) ? ((panel.fanInfo.control || {}).targets.gpu+'%') : 'automático')
                color: panel.muted; font.pixelSize: 10*panel.unit; Layout.fillWidth: true
            }
            Text { text: panel.message || ((panel.fanInfo.control || {}).error || (panel.saving ? 'Guardando…' : 'Activo: '+(panel.preferences.fanBoost ? 'Máximo · 100 %' : ((panel.fanInfo.control || {}).mode || 'Automático')))); color: panel.muted; font.pixelSize: 10*panel.unit; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Item { Layout.fillHeight: true }
        }
    }
}
