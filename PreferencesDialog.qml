pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    objectName: 'preferencesDialog'
    property var preferences: ({})
    property var fanInfo: ({})
    property var themes: []
    property string endpoint
    property color surface: '#211d2b'
    property color ink: '#f3dfcf'
    property color accent: '#ae96ef'
    property color muted: '#a49aae'
    property bool saving: false
    signal saved(var values)
    title: 'Personalizar dashboard'
    modal: true
    width: Math.min(620,parent ? parent.width-40 : 620)
    height: Math.min(760,parent ? parent.height-60 : 760)
    anchors.centerIn: parent
    palette.window: surface
    palette.base: Qt.darker(surface,1.12)
    palette.text: ink
    palette.windowText: ink
    palette.button: Qt.lighter(surface,1.3)
    palette.buttonText: ink
    palette.highlight: accent
    palette.highlightedText: surface
    background: Rectangle { radius: 22; color: dialog.surface; border.color: Qt.rgba(dialog.accent.r,dialog.accent.g,dialog.accent.b,0.4) }
    function resetControls() {
        let p=preferences;
        themeChoice.currentIndex=Math.max(0,themes.indexOf(p.theme || 'Lavanda'));
        raySwitch.checked=p.lightningEnabled===undefined?true:p.lightningEnabled;
        minimum.value=p.lightningMin || 5;maximum.value=p.lightningMax || 9;
        duration.value=Math.round((p.lightningDuration || 1.8)*10);
        refresh.value=Math.round((p.refreshInterval || 1000)/100);
        weather.value=p.weatherInterval || 10;
        backgroundControl.value=Math.round((p.backgroundOpacity===undefined?0.38:p.backgroundOpacity)*100);
        cards.value=Math.round((p.cardOpacity===undefined?0.66:p.cardOpacity)*100);
        fanEditor.reset(p);
        error.text='';
    }
    onOpened: resetControls()
    function save() {
        if(saving)return;
        let values={theme:themes[themeChoice.currentIndex],lightningEnabled:raySwitch.checked,lightningMin:minimum.value,lightningMax:maximum.value,lightningDuration:duration.value/10,refreshInterval:refresh.value*100,weatherInterval:weather.value,backgroundOpacity:backgroundControl.value/100,cardOpacity:cards.value/100};
        let fanValues=fanEditor.values();
        if(fanValues.fanMode!=='Automático' && !fanValues.fanChannels.length && !fanValues.fanGPU) {error.text='Selecciona un ventilador para aplicar el modo.';return}
        Object.assign(values,fanValues);
        saving=true;error.text='';
        let request=new XMLHttpRequest();request.open('POST',endpoint+'/settings');request.setRequestHeader('Content-Type','application/json');
        request.onreadystatechange=function() {
            if(request.readyState!==XMLHttpRequest.DONE)return;
            saving=false;
            if(request.status===200) {dialog.saved(JSON.parse(request.responseText));dialog.close()}
            else error.text='No se pudieron guardar los ajustes. Inténtalo otra vez.';
        };
        request.send(JSON.stringify(values));
    }
    component Caption: Label { color: dialog.ink; font.pixelSize: 14; wrapMode: Text.WordWrap }
    component Section: Label { color: dialog.accent; font.pixelSize: 12; font.bold: true; font.letterSpacing: 1; Layout.topMargin: 14 }
    contentItem: ScrollView {
        clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: parent.width; spacing: 10
            Section { text: 'APARIENCIA' }
            RowLayout { Layout.fillWidth: true
                Caption { text: 'Esquema de colores'; Layout.fillWidth: true }
                ComboBox { id: themeChoice; objectName: "settingsTheme"; model: dialog.themes; Layout.preferredWidth: 190 }
            }
            RowLayout { Layout.fillWidth: true
                Caption { text: 'Opacidad del fondo (%)'; Layout.fillWidth: true }
                SpinBox { id: backgroundControl; from: 0; to: 100; stepSize: 5; editable: true }
            }
            RowLayout { Layout.fillWidth: true
                Caption { text: 'Opacidad de los paneles (%)'; Layout.fillWidth: true }
                SpinBox { id: cards; from: 0; to: 100; stepSize: 5; editable: true }
            }
            Section { text: 'RAYOS' }
            RowLayout { Layout.fillWidth: true
                Caption { text: 'Efectos eléctricos'; Layout.fillWidth: true }
                Switch { id: raySwitch }
            }
            RowLayout { Layout.fillWidth: true; enabled: raySwitch.checked
                Caption { text: 'Espera mínima (segundos)'; Layout.fillWidth: true }
                SpinBox { id: minimum; objectName: "settingsMinimum"; from: 1; to: 300; editable: true; onValueModified: if(maximum.value<value) maximum.value=value }
            }
            RowLayout { Layout.fillWidth: true; enabled: raySwitch.checked
                Caption { text: 'Espera máxima (segundos)'; Layout.fillWidth: true }
                SpinBox { id: maximum; objectName: "settingsMaximum"; from: minimum.value; to: 300; editable: true }
            }
            Caption { text: 'Cada descarga aparece tras una espera aleatoria entre ambos valores.'; color: dialog.muted; font.pixelSize: 11; Layout.fillWidth: true }
            RowLayout { Layout.fillWidth: true; enabled: raySwitch.checked
                Caption { text: 'Duración de la descarga (segundos)'; Layout.fillWidth: true }
                SpinBox { id: duration; from: 5; to: 40; editable: true
                    textFromValue: function(v,locale) {return Number(v/10).toLocaleString(locale,'f',1)}
                    valueFromText: function(t,locale) {return Math.round(Number.fromLocaleString(locale,t)*10)}
                }
            }
            Section { text: 'ACTUALIZACIÓN' }
            RowLayout { Layout.fillWidth: true
                Caption { text: 'Métricas del sistema (segundos)'; Layout.fillWidth: true }
                SpinBox { id: refresh; from: 5; to: 50; stepSize: 5; editable: true
                    textFromValue: function(v,locale) {return Number(v/10).toLocaleString(locale,'f',1)}
                    valueFromText: function(t,locale) {return Math.round(Number.fromLocaleString(locale,t)*10)}
                }
            }
            RowLayout { Layout.fillWidth: true
                Caption { text: 'Clima (minutos)'; Layout.fillWidth: true }
                SpinBox { id: weather; from: 5; to: 60; stepSize: 5; editable: true }
            }
            FanProfilesEditor { id: fanEditor; objectName: "fanProfilesEditor"; Layout.fillWidth: true; fanInfo: dialog.fanInfo; ink: dialog.ink; accent: dialog.accent; muted: dialog.muted }
            Caption { text: 'Los cambios se guardan y se conservan al reiniciar.'; color: dialog.muted; font.pixelSize: 11; Layout.fillWidth: true }
            Caption { id: error; color: '#ef9696'; visible: text.length>0; Layout.fillWidth: true }
        }
    }
    footer: DialogButtonBox {
        Button { text: 'Cancelar'; enabled: !dialog.saving; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole; onClicked: dialog.close() }
        Button { text: dialog.saving ? 'Guardando…' : 'Guardar'; enabled: !dialog.saving; highlighted: true; DialogButtonBox.buttonRole: DialogButtonBox.ActionRole; onClicked: dialog.save() }
    }
}
