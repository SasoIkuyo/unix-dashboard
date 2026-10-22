pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window

Item {
    id: pc
    property color accent: '#ae96ef'
    property color ink: '#e7e6ed'
    property color muted: '#9da4b2'
    property real cpuRpm: 0
    property real gpuRpm: 0
    property bool animate: true
    property string lightingMode: 'Fijo'
    property string lightingTarget: 'Ambos'
    property real lightingSpeed: 50
    property real effectTime: 0
    property color effectColor: lightingMode==='Arcoíris' ? Qt.hsva((Math.floor(effectTime*10)/10)%1,0.85,1,1) : accent
    property real lightOpacity: lightingMode==='Apagado' ? 0 : lightingMode==='Respiración' ? 0.18+0.82*(0.5+0.5*Math.sin(effectTime*Math.PI*2)) : 1
    property real phase: 0
    Timer {
        interval: 42; repeat: true
        running: pc.animate && pc.visible && (!pc.Window.window || pc.Window.window.visibility !== Window.Minimized)
        onTriggered: {pc.phase = (pc.phase + interval / 1000) % 3600;pc.effectTime += interval/1000 * (0.08+pc.lightingSpeed/100*0.8)}
    }
    Item {
        id: artwork
        width: Math.min(pc.width, pc.height * 1.0) * 0.98
        height: width
        anchors.centerIn: parent
        Image {
            anchors.fill: parent
            source: 'pc3d/y70-realistic.png'
            fillMode: Image.PreserveAspectFit
            sourceSize.width: 768; sourceSize.height: 768
            smooth: true; mipmap: true
        }
        Repeater {
            model: [0.526,0.551]
            Rectangle {
                required property real modelData
                x: modelData*artwork.width; y: .327*artwork.height
                width: .009*artwork.width; height: .204*artwork.height
                radius: width/2; rotation: -1
                color: pc.effectColor
                opacity: pc.lightingTarget==='Placa' || pc.lightingTarget==='HyperX' ? 0 : pc.lightOpacity*0.85
            }
        }
        // Fixed photographic skin; small cached highlights are the only moving layer.
        Repeater {
            model: [
                {x:.285,y:.213,rx:.096,ry:.024,kind:'cpu'},
                {x:.480,y:.202,rx:.100,ry:.025,kind:'cpu'},
                {x:.701,y:.188,rx:.107,ry:.028,kind:'cpu'},
                {x:.775,y:.307,rx:.068,ry:.078,kind:'case'},
                {x:.775,y:.489,rx:.068,ry:.078,kind:'case'},
                {x:.775,y:.665,rx:.068,ry:.078,kind:'case'},
                {x:.166,y:.406,rx:.031,ry:.085,kind:'case'},
                {x:.386,y:.453,rx:.074,ry:.075,kind:'cpu'},
                {x:.214,y:.726,rx:.064,ry:.071,kind:'gpu'},
                {x:.377,y:.729,rx:.064,ry:.071,kind:'gpu'},
                {x:.541,y:.736,rx:.064,ry:.071,kind:'gpu'},
                {x:.286,y:.839,rx:.065,ry:.015,kind:'case'},
                {x:.512,y:.847,rx:.066,ry:.015,kind:'case'}
            ]
            Item {
                id: fan
                required property var modelData
                property real rpm: modelData.kind==='gpu' ? pc.gpuRpm : modelData.kind==='cpu' ? pc.cpuRpm : 700
                x: (modelData.x-modelData.rx)*artwork.width
                y: (modelData.y-modelData.ry)*artwork.height
                width: modelData.rx*2*artwork.width
                height: modelData.ry*2*artwork.height
                Rectangle {
                    anchors.centerIn: parent
                    width: fan.width; height: width; radius: width/2
                    visible: fan.modelData.kind!=='gpu' && pc.lightingTarget!=='RAM' && pc.lightingTarget!=='HyperX'
                    opacity: pc.lightOpacity
                    transform: Scale { origin.x: fan.width/2; origin.y: fan.width/2; yScale: fan.height/fan.width }
                    color: Qt.rgba(pc.effectColor.r,pc.effectColor.g,pc.effectColor.b,0.12)
                    border.width: Math.max(1,width*.025)
                    border.color: Qt.rgba(pc.effectColor.r,pc.effectColor.g,pc.effectColor.b,0.85)
                }
                Item {
                    anchors.centerIn: parent
                    width: parent.width; height: width
                    scale: 1
                    transform: Scale { origin.x: fan.width/2; origin.y: fan.width/2; yScale: fan.height/fan.width }
                    Canvas {
                        id: rotor
                        anchors.fill: parent
                        rotation: fan.rpm>0 ? (pc.phase*360/Math.max(1,1800/Math.max(1,fan.rpm)))%360 : 0
                        onWidthChanged: requestPaint()
                        Connections { target: pc; function onInkChanged() {rotor.requestPaint()} }
                        onPaint: {
                            let c=getContext('2d');c.reset();let r=width/2;
                            c.strokeStyle=Qt.rgba(pc.ink.r,pc.ink.g,pc.ink.b,0.15);c.lineWidth=Math.max(1,width*.025);
                            for(let i=0;i<7;i++) {let a=i*Math.PI*2/7;c.beginPath();c.arc(r,r,r*.66,a,a+.35);c.stroke()}
                        }
                    }
                }
            }
        }
    }
}
