pragma ComponentBehavior: Bound
import QtQuick

Item {
    id: pc
    property color accent: '#ae96ef'
    property color ink: '#e7e6ed'
    property color muted: '#9da4b2'
    property real cpuRpm: 0
    property real gpuRpm: 0
    property bool animate: true
    property real u: Math.min(width/380,height/300)
    Item {
        id: chassis
        width: 380; height: 300; scale: pc.u; transformOrigin: Item.TopLeft
        x: (pc.width-width*scale)/2; y: (pc.height-height*scale)/2
        Canvas {
            id: shell; anchors.fill: parent
            property color tint: pc.accent
            onTintChanged: requestPaint()
            onPaint: {
                let c=getContext('2d');c.reset();
                function poly(points,fill,stroke) {c.beginPath();c.moveTo(points[0][0],points[0][1]);for(let i=1;i<points.length;i++)c.lineTo(points[i][0],points[i][1]);c.closePath();if(fill){c.fillStyle=fill;c.fill()}if(stroke){c.strokeStyle=stroke;c.stroke()}}
                let edge='#cdd2db',white='#e3e7ee',steel='#7c8798',dark='#10141d',t=pc.accent;
                c.lineWidth=1.3;
                // Three-quarter view of the white panoramic glass case.
                let shadow=c.createLinearGradient(22,30,350,280);shadow.addColorStop(0,'#242936');shadow.addColorStop(1,'#070a10');
                poly([[23,33],[300,23],[350,49],[350,274],[76,288],[23,269]],shadow,steel);
                poly([[23,33],[300,23],[350,49],[76,63]],'#343a47',edge);
                for(let i=0;i<18;i++){c.strokeStyle='#596170';c.lineWidth=0.6;c.beginPath();c.moveTo(44+i*13,33);c.lineTo(91+i*13,57);c.stroke()}
                poly([[23,33],[76,63],[76,288],[23,269]],'#111620','#8b96a7');
                // Rear vents, motherboard tray and brushed white heatsinks.
                for(let i=0;i<11;i++){c.strokeStyle='#525d70';c.beginPath();c.moveTo(32+i*3,49+i*0.5);c.lineTo(32+i*3,83+i*0.5);c.stroke()}
                poly([[90,91],[236,85],[236,203],[90,210]],'#3b414c','#687487');
                poly([[95,94],[151,91],[144,108],[96,112]],'#c6cbd5',edge);
                poly([[95,115],[115,113],[115,167],[95,170]],'#b1b9c8',edge);
                for(let i=0;i<5;i++){c.strokeStyle='#8793a6';c.beginPath();c.moveTo(98+i*3,119);c.lineTo(98+i*3,163);c.stroke()}
                c.save();c.translate(106,154);c.rotate(-Math.PI/2);c.font='9px sans-serif';c.fillStyle='#697588';c.fillText('PRO RS',0,0);c.restore();
                for(let i=0;i<2;i++) {let x=202+i*12;c.fillStyle='#a0a9b9';c.fillRect(x,105,8,60);let grad=c.createLinearGradient(x,105,x,165);grad.addColorStop(0,Qt.lighter(t,1.6));grad.addColorStop(0.5,t);grad.addColorStop(1,'#e3d8ec');c.fillStyle=grad;c.fillRect(x+2,106,4,57)}
                // Power cable bundle behind the two RAM sticks.
                for(let i=0;i<5;i++){c.lineWidth=2;c.strokeStyle='#444b58';c.beginPath();c.moveTo(232+i*2,124);c.bezierCurveTo(253+i*2,130,243+i*2,156,275+i*2,161);c.stroke()}
                // Vertical GPU with three visible fans, like the reference photos.
                poly([[83,196],[262,187],[275,199],[275,254],[86,266]],'#161c26','#697487');
                poly([[83,196],[262,187],[275,199],[92,211]],'#465363','#a8b3c3');
                c.save();c.translate(96,207);c.rotate(-0.055);c.font='bold 9px sans-serif';c.fillStyle='#d1d7e0';c.fillText('GEFORCE RTX',0,0);c.restore();
                // AIO tubing is bright and braided, sweeping toward the top-right radiator.
                for(let j=0;j<2;j++) {
                    c.lineWidth=8;c.strokeStyle=j===0?'#b2bbc9':'#dce0e6';c.beginPath();c.moveTo(160+j*10,162);c.bezierCurveTo(187,217,312+j*6,211,296+j*9,66);c.stroke();
                    c.lineWidth=1;c.strokeStyle='#748195';c.beginPath();c.moveTo(158+j*10,163);c.bezierCurveTo(185,218,309+j*6,212,293+j*9,66);c.stroke();
                }
                // RGB floor rails and ventilation slots.
                for(let i=0;i<15;i++){c.strokeStyle='#455063';c.lineWidth=1;c.beginPath();c.moveTo(89+i*13,270-i*0.6);c.lineTo(98+i*13,280-i*0.6);c.stroke()}
                c.strokeStyle=Qt.rgba(t.r,t.g,t.b,0.7);c.lineWidth=3;c.beginPath();c.moveTo(84,281);c.lineTo(337,268);c.stroke();
                // Small collectible silhouette at the front of the GPU.
                c.fillStyle='#adb6c6';c.beginPath();c.arc(307,236,7,0,Math.PI*2);c.fill();
                poly([[300,230],[296,222],[302,226],[304,218],[307,224],[313,219],[313,227],[319,226],[315,232]],'#d0d6df',null);
                c.fillStyle='#505c72';c.fillRect(303,243,9,16);c.fillStyle='#3e4657';c.beginPath();c.save();c.translate(308,263);c.scale(12,4);c.arc(0,0,1,0,Math.PI*2);c.restore();c.fill();
                // Reflective glass and clean, thick white chassis rails.
                let glass=c.createLinearGradient(78,65,345,270);glass.addColorStop(0,Qt.rgba(1,1,1,0.03));glass.addColorStop(0.4,Qt.rgba(1,1,1,0.008));glass.addColorStop(1,Qt.rgba(1,1,1,0.045));
                poly([[77,64],[349,50],[349,273],[77,287]],glass,Qt.rgba(0.66,0.71,0.77,0.3));
                poly([[23,27],[301,17],[354,44],[350,52],[299,29],[24,39]],white,edge);
                poly([[23,265],[76,280],[350,267],[354,279],[75,295],[23,277]],white,edge);
                poly([[23,38],[28,40],[28,268],[23,265]],'#ccd3de',null);
                poly([[348,52],[354,50],[354,278],[348,275]],'#c6cdd8',null);
                c.fillStyle='#657084';c.fillRect(91,284,10,3);c.fillStyle=t;c.beginPath();c.arc(110,285,2,0,Math.PI*2);c.fill();
                // Thin front pane gives the case its panoramic corner.
                c.strokeStyle=Qt.rgba(0.89,0.91,0.94,0.44);c.lineWidth=1;c.beginPath();c.moveTo(278,55);c.lineTo(278,269);c.stroke();
            }
        }
        Repeater { model: 3
            Rotor { required property int index; x: 113+index*59; y: 43-index*2; width: 52; height: 27; rpm: pc.cpuRpm; tint: pc.accent; spinning: pc.animate }
        }
        Repeater { model: 2
            Rotor { required property int index; x: 126+index*64; y: 267-index*3; width: 55; height: 15; rpm: 700; tint: pc.accent; spinning: pc.animate; opacity: 0.7 }
        }
        Rotor { x: 91; y: 113; width: 28; height: 39; rpm: 700; tint: pc.accent; spinning: pc.animate; opacity: 0.7 }
        Repeater { model: 3
            Rotor { required property int index; x: 286; y: 82+index*49; width: 48; height: 47; rpm: 700; tint: pc.accent; spinning: pc.animate; opacity: 0.8 }
        }
        Rotor { pump: true; x: 133; y: 119; width: 58; height: 58; rpm: pc.cpuRpm; tint: pc.accent; spinning: pc.animate }
        Repeater { model: 3
            Rotor { required property int index; x: 99+index*54; y: 218-index*3; width: 43; height: 40; rpm: pc.gpuRpm; tint: pc.accent; spinning: pc.animate; darkHousing: true }
        }
    }
    component Rotor: Item {
        id: rotor
        property real rpm: 0
        property color tint
        property bool spinning: true
        property bool darkHousing: false
        property bool pump: false
        Rectangle { anchors.fill: parent; radius: rotor.pump ? Math.min(width,height)/2 : rotor.darkHousing ? 5 : 4; color: rotor.darkHousing ? '#151a23' : '#bfc8d9'; border.color: rotor.darkHousing ? '#69768a' : '#e4e8f0'; border.width: 1 }
        Item {
            anchors.centerIn: parent; width: Math.min(parent.width,parent.height)*0.83; height: width
            Canvas {
                id: blades; anchors.fill: parent
                property color tint: rotor.tint
                onTintChanged: requestPaint()
                onWidthChanged: requestPaint()
                onPaint: {
                    let c=getContext('2d');c.reset();let r=width/2;c.translate(r,r);
                    for(let i=0;i<7;i++) {c.save();c.rotate(i*Math.PI*2/7);c.beginPath();c.moveTo(0,0);c.bezierCurveTo(r*0.2,-r*0.3,r*0.75,-r*0.65,r*0.85,0);c.bezierCurveTo(r*0.65,-r*0.1,r*0.3,r*0.4,0,0);c.fillStyle=Qt.rgba(tint.r,tint.g,tint.b,rotor.darkHousing ? 0.55 : 0.9);c.fill();c.restore()}
                }
            }
            RotationAnimator on rotation { from: 0; to: 360; duration: Math.max(800,Math.min(6000,1800000/Math.max(1,rotor.rpm))); loops: Animation.Infinite; running: rotor.spinning && rotor.rpm>0 && rotor.visible }
        }
        Rectangle { width: parent.width*0.23; height: width; radius: width/2; anchors.centerIn: parent; color: rotor.darkHousing ? '#68778c' : '#d1d9e6'; border.width: 1; border.color: rotor.tint }
    }
}
