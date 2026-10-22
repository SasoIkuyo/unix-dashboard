pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: editor
    property var fanInfo: ({})
    property color ink: '#f3dfcf'
    property color muted: '#a49aae'
    property color accent: '#ae96ef'
    property var draftProfiles: ({'Silencioso':[35,45,70,100],'Equilibrado':[40,60,85,100],'Rendimiento':[55,75,95,100]})
    property var channels: []
    readonly property bool controlReady: fanInfo.controlReady || false
    spacing: 10
    function reset(p) {
        draftProfiles=JSON.parse(JSON.stringify(p.fanProfiles || {'Silencioso':[35,45,70,100],'Equilibrado':[40,60,85,100],'Rendimiento':[55,75,95,100]}));
        channels=(p.fanChannels || []).slice();gpu.checked=p.fanGPU || false;
        activeMode.currentIndex=Math.max(0,activeMode.model.indexOf(p.fanMode || 'Automático'));
        editMode.currentIndex=0;
    }
    function setPoint(index,value) {
        let profiles=JSON.parse(JSON.stringify(draftProfiles)),curve=profiles[editMode.currentText];curve[index]=value;
        for(let i=1;i<4;i++)curve[i]=Math.max(curve[i],curve[i-1]);
        draftProfiles=profiles;
    }
    function values() {return {fanBoost:false,fanMode:controlReady?activeMode.currentText:'Automático',fanChannels:channels,fanGPU:gpu.checked,fanProfiles:draftProfiles}}
    Label { text: 'VENTILACIÓN Y PERFILES'; color: editor.accent; font.bold: true; font.pixelSize: 12; font.letterSpacing: 1; Layout.topMargin: 14 }
    Repeater { model: (editor.fanInfo.rows || []).length
        RowLayout { id: readingRow; required property int index; property var row: editor.fanInfo.rows[index]; Layout.fillWidth: true
            Label { text: readingRow.row.label; color: editor.muted; Layout.fillWidth: true; font.pixelSize: 12 }
            Label { text: readingRow.row.rpm!==null ? readingRow.row.rpm+' RPM' : (readingRow.row.percent!==null ? readingRow.row.percent+'%' : '—'); color: editor.ink; font.pixelSize: 12 }
        }
    }
    Label { text: editor.controlReady ? 'Servicio de control disponible' : 'Lecturas activas. Instala el servicio para aplicar perfiles.'; color: editor.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 11 }
    RowLayout { Layout.fillWidth: true
        Label { text: 'Modo de uso'; color: editor.ink; Layout.fillWidth: true }
        ComboBox { id: activeMode; model: ['Automático','Silencioso','Equilibrado','Rendimiento']; enabled: editor.controlReady; Layout.preferredWidth: 180 }
    }
    Label { text: 'Dispositivos que controlará el modo'; color: editor.accent; font.pixelSize: 12 }
    Repeater { model: (editor.fanInfo.rows || []).filter(r=>r.source==='Placa' && r.rpm>0).length
        CheckBox {
            id: channelCheck
            required property int index
            property var row: editor.fanInfo.rows.filter(r=>r.source==='Placa' && r.rpm>0)[index]
            property int channel: Number(row.id.split(':fan')[1])
            text: channelCheck.row.label+' · conjunto CPU_FAN1'; enabled: editor.controlReady
            checked: editor.channels.indexOf(channel)>=0
            onClicked: {let selected=editor.channels.slice();let i=selected.indexOf(channel);if(checked && i<0)selected.push(channel);if(!checked && i>=0)selected.splice(i,1);editor.channels=selected}
        }
    }
    CheckBox { id: gpu; text: 'Ventiladores de la GPU NVIDIA'; enabled: editor.controlReady }
    Label { text: 'ARCTIC: mínimo del 50% para el conjunto; la bomba no se regula por separado. Automático devuelve el control al firmware.'; color: editor.muted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    RowLayout { Layout.fillWidth: true
        Label { text: 'Editar curva'; color: editor.ink; Layout.fillWidth: true }
        ComboBox { id: editMode; model: ['Silencioso','Equilibrado','Rendimiento']; Layout.preferredWidth: 180 }
    }
    Repeater { model: 3
        RowLayout { id: curveRow; required property int index; Layout.fillWidth: true
            Label { text: 'Velocidad a '+[40,60,75][curveRow.index]+' °C (%)'; color: editor.ink; Layout.fillWidth: true }
            SpinBox { from: 30; to: 100; editable: true; stepSize: 5; value: editor.draftProfiles[editMode.currentText][curveRow.index]; onValueModified: editor.setPoint(curveRow.index,value) }
        }
    }
    Label { text: 'A 85 °C se fuerza el 100%. Si el dashboard se cierra o pierde comunicación, el servicio restaura el control automático.'; color: editor.muted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
}
