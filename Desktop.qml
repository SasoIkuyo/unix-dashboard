import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    visible: true
    width: 968; height: 1858
    minimumWidth: 660; minimumHeight: 900
    title: "ARCH // WORKSTATION"
    property var metrics: ({})
    property var weatherInfo: metrics.weather || ({ready:false,status:'Elige tu ciudad',forecast:[]})
    property string selectedTheme: "Lavanda"
    property var palettes: ({
        'Obsidiana': ['#080808','#181013','#f05260','#f4e9eb','#c0a3a8','#ff7983'],
        'Lavanda': ['#100e18','#211d2b','#ae96ef','#f3dfcf','#a49aae','#edc68e'],
        'Océano': ['#0c141b','#182733','#83c8e4','#e0edf2','#94aab9','#edca9c'],
        'Bosque': ['#101610','#202b23','#a7c89a','#ede9d7','#a1b0a0','#e0c28e'],
        'Rosa': ['#1b1019','#30202e','#e4a0be','#f6e1e7','#b99ba9','#dfc097'],
        'Ámbar': ['#18130f','#2b241d','#dcb278','#f4e6d2','#b4a18d','#d9b0a1'],
        'Nord': ["#171d28", "#252f40", "#88c0d0", "#eceff4", "#a8b4c8", "#ebcb8b"],
        'Dracula': ["#171622", "#282638", "#bd93f9", "#f8f8f2", "#b6acce", "#ffb86c"],
        'Catppuccin': ["#11111b", "#252536", "#cba6f7", "#cdd6f4", "#a6adc8", "#fab387"],
        'Gruvbox': ["#1d2021", "#32302f", "#b8bb26", "#ebdbb2", "#bdae93", "#fabd2f"],
        'Tokio': ["#131521", "#24283b", "#7aa2f7", "#c0caf5", "#a1a9cf", "#e0af68"],
        'Solarizado': ["#00232c", "#073642", "#2aa198", "#eee8d5", "#a0b0aa", "#b58900"],
        'Carbón': ["#101112", "#242629", "#d6dce4", "#f4f5f7", "#abb0b8", "#c4b9a5"],
        'Rubí': ["#1b1015", "#30202a", "#ed889b", "#f7e3e8", "#bda2ae", "#e8bd94"],
        'Menta': ["#0c1717", "#1b2c2b", "#86d8be", "#e1f3ed", "#a0beb5", "#e7cd9c"],
        'Cobre': ["#1a120f", "#30231e", "#df9a70", "#f6e4d5", "#bfa796", "#e2c17a"]
    })
    property var paletteColors: selectedTheme === 'Caelestia' ? (metrics.systemPalette || palettes.Lavanda) : (palettes[selectedTheme] || palettes.Lavanda)
    property color bg: paletteColors[0]
    property color cardColor: paletteColors[1]
    property color accent: paletteColors[2]
    property color ink: paletteColors[3]
    property color muted: paletteColors[4]
    property color warm: paletteColors[5]
    property real unit: Math.max(0.55, Math.min(width/968, height/2180))
    property var preferences: ({})
    property bool lightningEnabled: preferences.lightningEnabled===undefined ? true : preferences.lightningEnabled
    property bool requestPending: false
    property string endpoint: 'http://127.0.0.1:' + Qt.application.arguments[Qt.application.arguments.length-1]
    // Only surfaces are translucent; text and indicators stay fully opaque.
    property real backgroundOpacity: preferences.backgroundOpacity===undefined ? 0.38 : preferences.backgroundOpacity
    property real cardOpacity: preferences.cardOpacity===undefined ? 0.66 : preferences.cardOpacity
    color: alpha(bg, backgroundOpacity)
    font.family: 'DejaVu Sans'
    function alpha(c,a) { return Qt.rgba(c.r,c.g,c.b,a) }
    function refresh() {
        if (requestPending) return;
        requestPending=true;
        let req = new XMLHttpRequest(); req.open('GET',endpoint+'/state');
        req.onreadystatechange = function() { if(req.readyState!==XMLHttpRequest.DONE) return; requestPending=false; if(req.status===200) { try { let value=JSON.parse(req.responseText); if(value.clock) {metrics=value; selectedTheme=value.theme; preferences=value.preferences || ({})} } catch(e) {} } }; req.send()
    }
    function chooseTheme(name) {
        selectedTheme=name
        let req=new XMLHttpRequest(); req.open('POST',endpoint+'/theme'); req.setRequestHeader('Content-Type','application/json'); req.send(JSON.stringify({theme:name}))
    }
    Timer { interval: root.preferences.refreshInterval || 1000; running: true; repeat: true; triggeredOnStart: true; onTriggered: root.refresh() }
    Shortcut { sequences: ['T','P']; onActivated: settingsPopup.visible ? settingsPopup.close() : settingsPopup.open() }
    Shortcut { sequence: 'R'; onActivated: root.refresh() }
    Shortcut { sequence: 'L'; enabled: !settingsPopup.visible && !cityDialog.visible; onActivated: { let req=new XMLHttpRequest(); req.open('POST',root.endpoint+'/settings'); req.setRequestHeader('Content-Type','application/json'); req.send(JSON.stringify({lightningEnabled:!root.lightningEnabled})); } }
    Shortcut { sequence: 'Q'; enabled: !settingsPopup.visible && !cityDialog.visible; onActivated: root.close() }
    component LabelText: Text {
        renderType: Text.NativeRendering
        color: root.ink; font.pixelSize: 14*root.unit
        elide: Text.ElideRight
    }
    component Card: Rectangle {
        objectName: "dashboardPanel"
        property string heading
        default property alias contents: body.data
        radius: 28*root.unit; color: root.alpha(root.cardColor, root.cardOpacity)
        border.width: 1; border.color: root.alpha(root.accent,0.09)
        LabelText { x: 24*root.unit; y: 22*root.unit; text: heading; color: root.accent; font.pixelSize: 14*root.unit; font.bold: true; font.letterSpacing: 1 }
        Item { id: body; anchors.fill: parent; anchors.margins: 24*root.unit; anchors.topMargin: 56*root.unit }
    }
    component Meter: Item {
        property real value: 0
        property color tint: root.accent
        property string number: ''
        property real reading: parseFloat(number) || 0
        Behavior on reading { NumberAnimation { duration: 350; easing.type: Easing.InOutCubic } }
        property string caption: ''
        property string detail: ''
        Canvas {
            id: ring; objectName: "gaugeRing"; width: Math.min(parent.width*0.82,parent.height-64*root.unit); height: width
            anchors.horizontalCenter: parent.horizontalCenter; y: 4*root.unit
            property real amount: parent.value
            Behavior on amount { NumberAnimation { duration: 350; easing.type: Easing.InOutCubic } }
            property color tint: parent.tint
            onAmountChanged: requestPaint()
            onTintChanged: requestPaint()
            onWidthChanged: requestPaint()
            Connections { target: root; function onPaletteColorsChanged() { ring.requestPaint() } }
            onPaint: {
                let c=getContext('2d'); c.reset(); let r=width/2-12*root.unit;
                c.lineWidth=14*root.unit; c.strokeStyle=root.alpha(root.accent,0.12); c.beginPath(); c.arc(width/2,height/2,r,0,Math.PI*2); c.stroke();
                c.lineWidth=2*root.unit; c.strokeStyle=root.alpha(root.accent,0.07); c.beginPath(); c.arc(width/2,height/2,r-18*root.unit,0,Math.PI*2); c.stroke();
                if(amount>0) {c.lineWidth=14*root.unit;c.lineCap='round';c.strokeStyle=tint;c.beginPath();c.arc(width/2,height/2,r,-Math.PI/2,-Math.PI/2+Math.PI*2*Math.min(100,amount)/100);c.stroke()}
            }
            LabelText { anchors.centerIn: parent; text: number.endsWith('%') ? Math.round(reading)+'%' : reading.toFixed(2); color: root.ink; font.pixelSize: Math.min(33*root.unit,ring.width*0.26); font.weight: Font.DemiBold; width: parent.width*0.92; horizontalAlignment: Text.AlignHCenter }
        }
        Column { anchors.top: ring.bottom; anchors.topMargin: 10*root.unit; width: parent.width; spacing: 7*root.unit
            LabelText { width: parent.width; horizontalAlignment: Text.AlignHCenter; text: caption; color: tint; font.pixelSize: 14*root.unit; font.bold: true }
            LabelText { width: parent.width; horizontalAlignment: Text.AlignHCenter; text: detail; color: root.muted; font.pixelSize: 11*root.unit; wrapMode: Text.WordWrap; maximumLineCount: 2 }
        }
    }
    component Graph: Item {
        property var values: []
        property color tint: root.accent
        property string caption
        LabelText { text: caption; color: root.muted; font.pixelSize: 12*root.unit }
        LabelText { anchors.right: parent.right; text: values.length ? Number(values[values.length-1]).toFixed(0)+'°' : '—'; color: tint; font.bold: true }
        Canvas {
            id: plot; objectName: "historyPlot"; anchors.fill: parent; anchors.topMargin: 30*root.unit
            property var values: parent.values
            property var previousPoints: []
            property var nextPoints: []
            property real progress: 1
            property real lower: values.length ? Math.floor((Math.min.apply(null,values)-3)/5)*5 : 30
            property real upper: values.length ? Math.ceil((Math.max.apply(null,values)+3)/5)*5 : 60
            Behavior on lower { NumberAnimation { duration: 350 } }
            Behavior on upper { NumberAnimation { duration: 350 } }
            onLowerChanged: requestPaint()
            onUpperChanged: requestPaint()
            function displayedPoints() {
                return nextPoints.map((v,i) => previousPoints.length ? previousPoints[i]+(v-previousPoints[i])*progress : v)
            }
            function updatePoints() {
                if (!values.length) return;
                let padded=Array(Math.max(0,90-values.length)).fill(values[0]).concat(values).slice(-90);
                if (JSON.stringify(padded)===JSON.stringify(nextPoints)) return;
                let current=displayedPoints();
                transition.stop(); previousPoints=current.length ? current : padded;
                nextPoints=padded; progress=0; transition.start();
            }
            NumberAnimation { id: transition; target: plot; property: 'progress'; from: 0; to: 1; duration: 350; easing.type: Easing.InOutCubic }
            onProgressChanged: requestPaint()
            property color tint: parent.tint
            onValuesChanged: updatePoints()
            onTintChanged: requestPaint()
            onWidthChanged: requestPaint()
            Connections { target: root; function onPaletteColorsChanged() { plot.requestPaint() } }
            onPaint: {
                let c=getContext('2d');c.reset(); if(!values.length)return;
                let lo=lower,hi=Math.max(lower+1,upper);
                let pts=displayedPoints(); if(!pts.length)return;
                let grad=c.createLinearGradient(0,0,0,height);grad.addColorStop(0,root.alpha(tint,0.3));grad.addColorStop(1,root.alpha(tint,0.015));
                c.beginPath();c.moveTo(0,height);
                for(let i=0;i<pts.length;i++)c.lineTo(i/(pts.length-1)*width,height-8-(pts[i]-lo)/(hi-lo)*(height-16));
                c.lineTo(width,height);c.closePath();c.fillStyle=grad;c.fill();c.beginPath();
                for(let i=0;i<pts.length;i++) {let x=i/(pts.length-1)*width,y=height-8-(pts[i]-lo)/(hi-lo)*(height-16);if(i===0)c.moveTo(x,y);else c.lineTo(x,y)}
                c.strokeStyle=tint;c.lineWidth=2*root.unit;c.stroke();
            }
        }
    }
    component AppRows: ColumnLayout {
        property var rows: []
        property real maximum: Math.max(1,...rows.map(d=>d.seconds))
        spacing: 7*root.unit
        Repeater { model: parent.rows.length; delegate: RowLayout {
            required property int index
            property var entry: parent.rows[index]
            Layout.fillWidth: true
            Image { source: 'image://appicons/'+(entry.iconName || 'application-x-executable'); Layout.preferredWidth: 18*root.unit; Layout.preferredHeight: 18*root.unit; sourceSize.width: 36; sourceSize.height: 36; fillMode: Image.PreserveAspectFit; cache: true }
            LabelText { text: entry.name; Layout.preferredWidth: 78*root.unit; font.pixelSize: 11*root.unit }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 11*root.unit; radius: height/2; color: root.alpha(root.accent,0.1)
                Rectangle { width: parent.width*entry.seconds/parent.parent.parent.maximum; height: parent.height; radius: height/2; color: root.accent
                    Behavior on width { NumberAnimation { duration: 350; easing.type: Easing.InOutCubic } }
                }
            }
            LabelText { text: entry.duration; Layout.preferredWidth: 59*root.unit; horizontalAlignment: Text.AlignRight; font.pixelSize: 10*root.unit; color: root.muted }
        }}
    }
    PreferencesDialog {
        id: settingsPopup
        preferences: root.preferences
        fanInfo: root.metrics.fans || ({})
        themes: themePicker.model
        endpoint: root.endpoint
        surface: root.cardColor; ink: root.ink; accent: root.accent; muted: root.muted
        onSaved: function(values) {root.preferences=values;root.selectedTheme=values.theme;root.refresh()}
    }
    Dialog {
        id: cityDialog; title: 'Ciudad del clima'; modal: true; anchors.centerIn: parent; width: 400*root.unit
        standardButtons: Dialog.Ok | Dialog.Cancel
        background: Rectangle { color: root.cardColor; radius: 18*root.unit; border.color: root.accent }
        contentItem: ColumnLayout {
            LabelText { text: 'Escribe ciudad y país, por ejemplo: Santiago, Chile'; color: root.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            TextField { id: cityInput; Layout.fillWidth: true; placeholderText: 'Ciudad, país'; color: root.ink; maximumLength: 120; selectByMouse: true; onAccepted: if(text.trim().length>=2) cityDialog.accept() }
        }
        onOpened: cityInput.forceActiveFocus()
        onAccepted: {
            if(cityInput.text.trim().length<2) return;
            let request=new XMLHttpRequest(); request.open('POST',root.endpoint+'/weather'); request.setRequestHeader('Content-Type','application/json'); request.send(JSON.stringify({city:cityInput.text.trim()}));
        }
    }
    // The background remains quiet, with a single soft organic accent.
    Rectangle { width: root.width*0.65; height: root.height*0.8; x: root.width*0.67; y: -height*0.2; radius: width/2; rotation: 28; color: root.alpha(root.accent,0.035) }
    ColumnLayout {
        id: dashboardLayout
        objectName: 'dashboardLayout'
        anchors.fill: parent; anchors.margins: 18*root.unit
        spacing: 12*root.unit
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 48*root.unit
            LabelText { text: '◭  ARCH / WORKSTATION'; color: root.accent; font.pixelSize: 20*root.unit; font.bold: true; Layout.fillWidth: true }
            LabelText { text: '● LIVE'; color: '#a9c8ae'; font.pixelSize: 11*root.unit }
            Button {
                text: '⚙ Ajustes'
                onClicked: settingsPopup.open()
                contentItem: LabelText { text: parent.text; color: root.accent; font.pixelSize: 11*root.unit; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { color: root.cardColor; radius: 12 }
            }
            ComboBox {
                id: themePicker; model: ["Lavanda", "Océano", "Bosque", "Rosa", "Ámbar", "Nord", "Dracula", "Catppuccin", "Gruvbox", "Tokio", "Solarizado", "Carbón", "Rubí", "Menta", "Cobre", "Obsidiana", "Caelestia"]; Layout.preferredWidth: 165*root.unit
                currentIndex: model.indexOf(root.selectedTheme)
                onActivated: root.chooseTheme(currentText)
                contentItem: LabelText { text: themePicker.currentText; verticalAlignment: Text.AlignVCenter; leftPadding: 12; color: root.accent }
                background: Rectangle { radius: 14; color: root.cardColor; border.color: root.alpha(root.accent,0.2) }
                delegate: ItemDelegate { width: themePicker.width; text: modelData; highlighted: themePicker.highlightedIndex===index }
            }
        }
        RowLayout {
            spacing: 16*root.unit; Layout.fillWidth: true; Layout.preferredHeight: 185*root.unit
            Card {
                heading: 'HORA LOCAL'; Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1
                ClockFace {
                    anchors.fill: parent
                    timeText: root.metrics.clock || '00:00'
                    secondsText: root.metrics.seconds || '00'
                    dateText: root.metrics.date || ''
                    accent: root.accent; ink: root.ink; muted: root.muted; unit: root.unit
                }

            }
            Card {
                heading: 'SEMANA '+(root.metrics.week || '')+' / 52'; Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1
                Column { width: parent.width; spacing: 18*root.unit
                    Row { width: parent.width
                        Repeater { model: ['L','M','X','J','V','S','D']; delegate: Column { required property int index; required property string modelData; width: parent.width/7; spacing: 9*root.unit
                            LabelText { width: parent.width; horizontalAlignment: Text.AlignHCenter; text: modelData; color: root.muted; font.pixelSize: 12*root.unit }
                            Rectangle { width: parent.width-6; height: 28*root.unit; radius: 8*root.unit; color: index===root.metrics.weekday?root.accent:root.alpha(root.accent,0.06)
                                LabelText { anchors.centerIn: parent; text: root.metrics.weekDates ? root.metrics.weekDates[index] : '·'; color: index===root.metrics.weekday?root.bg:root.muted; font.pixelSize: 12*root.unit }
                            }
                        }}
                    }
                    Rectangle { width: parent.width; height: 9*root.unit; radius: height/2; color: root.alpha(root.accent,0.12); Rectangle { width: parent.width*((root.metrics.weekday+1)/7 || 0); height: parent.height; radius: height/2; color: root.accent; Behavior on width { NumberAnimation { duration: 350; easing.type: Easing.InOutCubic } } } }
                    LabelText { text: 'Día '+((root.metrics.weekday || 0)+1)+' de 7 · '+(root.metrics.yearProgress || '')+' del año'; color: root.muted; font.pixelSize: 12*root.unit }
                }
            }
        }
        Card {
            heading: 'CLIMA'+(root.weatherInfo.city ? ' / '+root.weatherInfo.city.toUpperCase() : '')
            Layout.fillWidth: true; Layout.preferredHeight: 175*root.unit
            Button {
                anchors.right: parent.right; y: -42*root.unit; height: 27*root.unit
                text: root.weatherInfo.city ? 'Cambiar ciudad' : 'Elegir ciudad'
                onClicked: { cityInput.text=root.weatherInfo.query || ''; cityDialog.open() }
                contentItem: LabelText { text: parent.text; color: root.accent; font.pixelSize: 10*root.unit; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { radius: 10*root.unit; color: root.alpha(root.accent,0.1) }
            }
            RowLayout { anchors.fill: parent; spacing: 18*root.unit
                ColumnLayout { Layout.preferredWidth: 235*root.unit; Layout.maximumWidth: 265*root.unit; Layout.minimumWidth: 235*root.unit; Layout.fillHeight: true; spacing: 3*root.unit
                    RowLayout {
                        LabelText { text: root.weatherInfo.icon || '☁'; font.pixelSize: 35*root.unit; color: root.warm }
                        LabelText { text: root.weatherInfo.ready ? root.weatherInfo.temperature+'°' : '—'; font.pixelSize: 40*root.unit; font.weight: Font.Light }
                        LabelText { text: root.weatherInfo.status || ''; color: root.muted; font.pixelSize: 10*root.unit; Layout.preferredWidth: 120*root.unit; wrapMode: Text.WordWrap; maximumLineCount: 2 }
                    }
                    LabelText { text: root.weatherInfo.ready ? 'Sensación '+root.weatherInfo.feels+'° · humedad '+root.weatherInfo.humidity+'%' : 'Configura tu ciudad para ver el pronóstico'; color: root.muted; font.pixelSize: 10*root.unit; Layout.fillWidth: true }
                    LabelText { text: root.weatherInfo.ready ? 'Viento '+root.weatherInfo.wind+' km/h · '+(root.weatherInfo.stale ? 'datos guardados' : root.weatherInfo.updated) : ''; color: root.muted; font.pixelSize: 9*root.unit; Layout.fillWidth: true }
                }
                RowLayout { Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumWidth: 450*root.unit; spacing: 6*root.unit
                    Repeater { objectName: 'weatherRepeater'; model: (root.weatherInfo.forecast || []).length
                        ColumnLayout { required property int index; property var day: root.weatherInfo.forecast[index]; Layout.fillWidth: true; Layout.preferredWidth: 1; spacing: 5*root.unit
                            LabelText { text: day.day; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; color: root.muted; font.pixelSize: 11*root.unit }
                            LabelText { text: day.icon; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; color: root.warm; font.pixelSize: 23*root.unit }
                            LabelText { text: day.high+'° / '+day.low+'°'; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 11*root.unit }
                            LabelText { text: '☂ '+day.rain+'%'; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; color: root.muted; font.pixelSize: 9*root.unit }
                        }
                    }
                }
            }
            LabelText { anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.bottomMargin: -15*root.unit; text: 'Open-Meteo ↗'; font.pixelSize: 8*root.unit; color: root.muted
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: Qt.openUrlExternally('https://open-meteo.com/') }
            }
        }
        Card {
            objectName: 'dashboardPanel'
            heading: (coolingPanel.lightingView ? 'ILUMINACIÓN' : 'REFRIGERACIÓN')+' · HYTE Y70'
            Layout.fillWidth: true; Layout.preferredHeight: 350*root.unit; Layout.minimumHeight: 340*root.unit
            CoolingPanel {
                id: coolingPanel
                objectName: 'coolingPanel'
                lightingInfo: root.metrics.lighting || ({})
                anchors.fill: parent
                fanInfo: root.metrics.fans || ({})
                preferences: root.preferences
                endpoint: root.endpoint
                accent: root.accent; ink: root.ink; muted: root.muted; unit: root.unit
                onSaved: function(values) {root.preferences=values;root.refresh()}
                onEditTargets: settingsPopup.open()
            }
        }
        RowLayout {
            spacing: 16*root.unit; Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredHeight: 560*root.unit
            Card {
                heading: 'RECURSOS'; Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1.12
                GridLayout { anchors.fill: parent; columns: 2; columnSpacing: 8*root.unit; rowSpacing: 12*root.unit
                    Repeater { objectName: "gaugesRepeater"; model: (root.metrics.gauges || []).length; delegate: Meter { property var modelData: root.metrics.gauges[index]; required property int index; Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1; Layout.preferredHeight: 1; value: modelData.value; number: modelData.text; caption: modelData.label; detail: modelData.detail; tint: index===2?root.warm:root.accent } }
                }

            }
            Card {
                heading: 'TÉRMICAS · ACT / MÍN / MÁX'; Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1
                ColumnLayout { anchors.fill: parent; spacing: 10*root.unit
                    Repeater { objectName: "thermsRepeater"; model: (root.metrics.therms || []).length; delegate: RowLayout { required property int index; property var modelData: root.metrics.therms[index]; Layout.fillWidth: true; spacing: 7*root.unit
                        LabelText { text: modelData.sensor || modelData.label; color: root.muted; font.pixelSize: 11*root.unit; Layout.preferredWidth: 70*root.unit }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 8*root.unit; radius: 4; color: root.alpha(root.accent,0.1); Rectangle { width: parent.width*Math.min(1,modelData.value/100); height: parent.height; radius: 4; color: root.accent; Behavior on width { NumberAnimation { duration: 350; easing.type: Easing.InOutCubic } } } }
                        LabelText { text: Number(modelData.value).toFixed(1)+'°'; font.pixelSize: 12*root.unit; Layout.preferredWidth: 45*root.unit; horizontalAlignment: Text.AlignRight }
                        LabelText { text: Number(modelData.low).toFixed(0)+' / '+Number(modelData.high).toFixed(0)+'°'; color: root.muted; font.pixelSize: 9*root.unit; Layout.preferredWidth: 55*root.unit; horizontalAlignment: Text.AlignRight }
                    }}
                    LabelText { text: 'Sesión  mín '+(root.metrics.thermalMinimum || '—')+'   máx '+(root.metrics.thermalMaximum || '—'); color: root.muted; font.pixelSize: 10*root.unit; Layout.fillWidth: true }
                    Graph { Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 55*root.unit; caption: 'CPU · últimos 90 registros'; values: root.metrics.cpuHistory || [] }
                    Graph { Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 55*root.unit; caption: 'GPU · últimos 90 registros'; tint: root.warm; values: root.metrics.gpuHistory || [] }
                }
            }
        }
        RowLayout {
            spacing: 16*root.unit; Layout.fillWidth: true; Layout.preferredHeight: 480*root.unit; Layout.minimumHeight: 470*root.unit
            Card {
                heading: 'ACTIVIDAD'; Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1
                ColumnLayout { anchors.fill: parent; spacing: 10*root.unit
                    LabelText { text: root.metrics.month || ''; font.pixelSize: 17*root.unit }
                    GridLayout { Layout.fillWidth: true; Layout.fillHeight: true; columns: 7; rowSpacing: 3*root.unit; columnSpacing: 3*root.unit
                        Repeater { model: ['L','M','X','J','V','S','D']; LabelText { required property string modelData; text: modelData; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; color: root.muted; font.pixelSize: 11*root.unit } }
                        Repeater { objectName: "daysRepeater"; model: (root.metrics.days || []).length; delegate: Rectangle { required property int index; property var modelData: root.metrics.days[index]; Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1; Layout.preferredHeight: 1; radius: 9*root.unit; color: modelData.today?root.accent:modelData.value>0?root.alpha(root.accent,Math.min(0.65,0.12+modelData.value/60000)):'transparent'
                            LabelText { anchors.centerIn: parent; text: modelData.day; font.pixelSize: 12*root.unit; color: modelData.today?root.bg:modelData.current?root.ink:root.alpha(root.muted,0.3) }
                            ToolTip.visible: hover.hovered; ToolTip.text: modelData.duration
                            HoverHandler { id: hover }
                        }}
                    }
                    LabelText { text: (root.metrics.total || '—')+' este mes · '+(root.metrics.activeDays || 0)+' días activos'; color: root.muted; font.pixelSize: 11*root.unit; Layout.fillWidth: true }
                    LabelText { text: 'Media '+(root.metrics.monthAverage || '—')+' · racha '+(root.metrics.streak || 0)+' días'; color: root.muted; font.pixelSize: 10*root.unit; Layout.fillWidth: true }
                    LabelText { text: 'Hoy '+(root.metrics.today || '—')+' · mejor día '+(root.metrics.bestDay || '—'); color: root.muted; font.pixelSize: 10*root.unit; Layout.fillWidth: true }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 8*root.unit; radius: 4; color: root.alpha(root.accent,0.1); Rectangle { width: parent.width*(root.metrics.day/root.metrics.monthDays || 0); height: parent.height; radius: 4; color: root.accent; Behavior on width { NumberAnimation { duration: 350; easing.type: Easing.InOutCubic } } } }
                }
            }
            Card {
                heading: 'UPTIME · PRESENCIA'; Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1
                ColumnLayout { anchors.fill: parent; spacing: 5*root.unit
                    Repeater { id: uptimeRows; property var rows: [{label:'Sistema encendido',value:root.metrics.uptime},{label:'Sesión actual',value:root.metrics.session},{label:'Hoy',value:root.metrics.today},{label:'Este mes',value:root.metrics.total},{label:'Media por día',value:root.metrics.monthAverage},{label:'Racha',value:(root.metrics.streak || 0)+' días'}]; model: 6
                        RowLayout { required property int index; property var modelData: uptimeRows.rows[index]; Layout.fillWidth: true
                            LabelText { text: modelData.label; color: root.muted; font.pixelSize: 12*root.unit; Layout.fillWidth: true }
                            LabelText { text: modelData.value || '—'; font.pixelSize: 13*root.unit; font.bold: true }
                        }
                    }
                    LabelText { text: 'ÚLTIMOS 7 DÍAS'; color: root.accent; font.pixelSize: 11*root.unit; Layout.topMargin: 6*root.unit }
                    Repeater { objectName: "weekDaysRepeater"; model: (root.metrics.weekDays || []).length; delegate: RowLayout { required property int index; property var modelData: root.metrics.weekDays[index]; Layout.fillWidth: true
                        LabelText { text: modelData.label; color: root.muted; font.pixelSize: 10*root.unit; Layout.preferredWidth: 47*root.unit }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 10*root.unit; radius: 4; color: root.alpha(root.accent,0.04); Rectangle { width: parent.width*modelData.seconds/Math.max(1,...(root.metrics.weekDays || []).map(d=>d.seconds)); height: parent.height; radius: 4; color: root.accent; Behavior on width { NumberAnimation { duration: 350; easing.type: Easing.InOutCubic } } } }
                        LabelText { text: modelData.duration; font.pixelSize: 10*root.unit; Layout.preferredWidth: 53*root.unit; horizontalAlignment: Text.AlignRight }
                    }}
                    LabelText { text: '30 DÍAS'; color: root.accent; font.pixelSize: 10*root.unit }
                    Row { Layout.fillWidth: true; Layout.preferredHeight: 24*root.unit; spacing: 2*root.unit
                        Repeater { model: 30; Rectangle { required property int index; width: (parent.width-58*root.unit)/30; height: Math.max(2*root.unit,24*root.unit*((root.metrics.history30 || [])[index] || 0)/Math.max(1,...(root.metrics.history30 || []))); y: 24*root.unit-height; radius: 1; color: root.accent
                            Behavior on height { NumberAnimation { duration: 350; easing.type: Easing.InOutCubic } }
                        }}
                    }
                    LabelText { text: 'Máx '+(root.metrics.historyMaximum || '—')+' · media '+(root.metrics.historyAverage || '—'); color: root.muted; font.pixelSize: 9*root.unit; Layout.fillWidth: true }
                    Item { Layout.fillHeight: true }
                    LabelText { text: (root.metrics.cpuName || '')+' · '+(root.metrics.ramTotal || ''); color: root.muted; font.pixelSize: 9*root.unit; Layout.fillWidth: true; wrapMode: Text.WordWrap; maximumLineCount: 2 }
                }
            }
        }
        Card {
            heading: 'APLICACIONES · HOY'; Layout.fillWidth: true; Layout.preferredHeight: 310*root.unit
            RowLayout { anchors.fill: parent; spacing: 24*root.unit
                ColumnLayout { Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1
                    LabelText { text: 'Sesión '+(root.metrics.session || '—')+' · tiempo por ventana'; color: root.muted; font.pixelSize: 10*root.unit }
                    AppRows { Layout.fillWidth: true; rows: root.metrics.apps || [] }
                    LabelText { visible: !(root.metrics.apps || []).length; text: 'Sin actividad registrada hoy'; color: root.muted }
                    Item { Layout.fillHeight: true }
                }
                ColumnLayout { Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1; spacing: 7*root.unit
                    LabelText { text: 'ÚLTIMOS 7 DÍAS'; color: root.accent; font.pixelSize: 11*root.unit }
                    AppRows { Layout.fillWidth: true; rows: root.metrics.appsWeek || [] }
                    LabelText { text: 'RESUMEN'; color: root.accent; font.pixelSize: 10*root.unit; Layout.topMargin: 6*root.unit }
                    LabelText { text: 'Presencia '+(root.metrics.today || '—')+' · registrado '+(root.metrics.registered || '—'); color: root.muted; font.pixelSize: 10*root.unit; Layout.fillWidth: true }
                    LabelText { text: 'Sin ventana '+(root.metrics.idle || '—')+' · '+(root.metrics.appCount || 0)+' aplicaciones'; color: root.muted; font.pixelSize: 10*root.unit; Layout.fillWidth: true }
                    Item { Layout.fillHeight: true }
                }
            }
        }
        RowLayout { Layout.fillWidth: true; Layout.preferredHeight: 16*root.unit
            LabelText { text: 'T / P · ajustes   L · rayos   R · refrescar   Q · salir'; color: root.muted; font.pixelSize: 10*root.unit; Layout.fillWidth: true }
            LabelText { text: (root.metrics.host || '')+' · '+(root.metrics.kernel || ''); color: root.muted; font.pixelSize: 10*root.unit }
        }
    }
    Lightning {
        objectName: "lightningEffect"
        anchors.fill: parent
        z: 20
        tint: root.accent
        minimumInterval: root.preferences.lightningMin || 5
        maximumInterval: root.preferences.lightningMax || 9
        durationSeconds: root.preferences.lightningDuration || 1.8
        panelProvider: function() {
            let rectangles=[];
            function visit(item) {
                if(item.objectName==='dashboardPanel') {
                    let position=item.mapToItem(root.contentItem,0,0);
                    if(position.y+item.height>0 && position.y<root.height) rectangles.push({x:position.x,y:position.y,width:item.width,height:item.height,radius:item.radius});
                }
                for(let child of item.children || []) visit(child);
            }
            visit(root.contentItem);
            return rectangles;
        }
        scaleFactor: root.unit
        effectEnabled: root.lightningEnabled && root.visible && root.visibility !== Window.Minimized
    }

}
