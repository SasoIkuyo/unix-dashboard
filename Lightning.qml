import QtQuick

Item {
    id: effect
    // Fine filaments and branching arcs tinted by the active dashboard palette.
    property color tint: '#65baff'
    property real scaleFactor: 1
    property bool effectEnabled: true
    property real minimumInterval: 5
    property real maximumInterval: 9
    property real durationSeconds: 1.8
    onMinimumIntervalChanged: { if(!animating) schedule() }
    onMaximumIntervalChanged: { if(!animating) schedule() }
    property var panelProvider: null
    property var paths: []
    property real reveal: 0
    property real glow: 0
    property real phase: 0
    readonly property bool animating: strike.running

    function outline(rect) {
        let r=Math.min(rect.radius,rect.width/2,rect.height/2), points=[];
        let corners=[{x:rect.x+r,y:rect.y+r,a:180},{x:rect.x+rect.width-r,y:rect.y+r,a:270},{x:rect.x+rect.width-r,y:rect.y+rect.height-r,a:0},{x:rect.x+r,y:rect.y+rect.height-r,a:90}];
        for(let corner of corners)for(let i=0;i<=6;i++) {let a=(corner.a+i*15)*Math.PI/180;points.push({x:corner.x+Math.cos(a)*r,y:corner.y+Math.sin(a)*r})}
        return points;
    }
    function atDistance(points,distance) {
        let lengths=[],total=0;
        for(let i=0;i<points.length;i++) {let a=points[i],b=points[(i+1)%points.length];let l=Math.hypot(b.x-a.x,b.y-a.y);lengths.push(l);total+=l}
        distance=((distance%total)+total)%total;
        for(let i=0;i<points.length;i++) {
            if(distance<=lengths[i]) {let a=points[i],b=points[(i+1)%points.length],t=distance/Math.max(0.01,lengths[i]);return {x:a.x+(b.x-a.x)*t,y:a.y+(b.y-a.y)*t}}
            distance-=lengths[i];
        }
        return points[0];
    }
    function trigger() {
        if(!effectEnabled || width<40 || height<100)return;
        cadence.stop();
        let rects=panelProvider ? panelProvider() : [];
        if(!rects.length)rects=[{x:22,y:55,width:width-44,height:height-110,radius:28}];
        let strokes=[];
        for(let k=0;k<4;k++) {
            let rect=rects[Math.floor(Math.random()*rects.length)], guide=outline(rect);
            let length=(200+Math.random()*320)*scaleFactor,start=Math.random()*2*(rect.width+rect.height),direction=Math.random()<0.5?1:-1;
            let vertices=[],forks=[];
            for(let i=0;i<=48;i++) {
                let p=atDistance(guide,start+direction*length*i/48);
                let seed=Math.random()*Math.PI*2;
                vertices.push({x:p.x+(Math.random()-0.5)*18*scaleFactor,y:p.y+(Math.random()-0.5)*18*scaleFactor,seed:seed});
                if(i>3 && i<44 && i%8===0) {
                    let angle=Math.random()*Math.PI*2,reach=(16+Math.random()*20)*scaleFactor;
                    forks.push({at:i,dx:Math.cos(angle)*reach,dy:Math.sin(angle)*reach});
                }
            }
            strokes.push({points:vertices,branches:forks,delay:k*0.035});
        }
        paths=strokes;phase=0;reveal=0;glow=0;strike.restart();
    }
    function schedule() { if(effectEnabled) {cadence.interval=Math.round((minimumInterval+Math.random()*Math.max(0,maximumInterval-minimumInterval))*1000);cadence.restart()} }
    onEffectEnabledChanged: { if(!effectEnabled) {cadence.stop();strike.stop();glow=0} else schedule() }
    onRevealChanged: bolts.requestPaint()
    onPhaseChanged: bolts.requestPaint()
    onTintChanged: bolts.requestPaint()
    Canvas {
        id: bolts
        anchors.fill: parent
        opacity: effect.glow
        visible: opacity>0
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            let ctx=getContext('2d');ctx.reset();ctx.lineCap='round';ctx.lineJoin='round';
            let widths=[26,13,4,1.1],base=effect.tint,
                colors=[base,base,Qt.lighter(base,1.18),Qt.rgba(base.r*0.3+0.7,base.g*0.3+0.7,base.b*0.3+0.7,1)],strengths=[0.025,0.10,0.46,0.98];
            function vertex(p) {return {x:p.x+Math.sin(p.seed+effect.phase*1.5)*2.5*effect.scaleFactor,y:p.y+Math.cos(p.seed+effect.phase)*2.5*effect.scaleFactor}}
            for(let stroke of effect.paths) {
                let count=Math.max(2,Math.ceil(Math.max(0,Math.min(1,(effect.reveal-stroke.delay)/(1-stroke.delay)))*stroke.points.length));
                for(let pass=0;pass<4;pass++) {
                    let color=colors[pass];ctx.strokeStyle=Qt.rgba(color.r,color.g,color.b,strengths[pass]);ctx.lineWidth=widths[pass]*effect.scaleFactor;
                    ctx.beginPath();
                    for(let i=0;i<Math.min(count,stroke.points.length);i++) {let p=vertex(stroke.points[i]);if(i===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y)}
                    ctx.stroke();
                    for(let branch of stroke.branches) {
                        if(branch.at>=count)continue;
                        let p=vertex(stroke.points[branch.at]);ctx.beginPath();ctx.moveTo(p.x,p.y);
                        ctx.lineTo(p.x+branch.dx*0.25+4*effect.scaleFactor,p.y+branch.dy*0.25);
                        ctx.lineTo(p.x+branch.dx*0.5-3*effect.scaleFactor,p.y+branch.dy*0.55);
                        ctx.lineTo(p.x+branch.dx*0.75+2*effect.scaleFactor,p.y+branch.dy*0.7);
                        ctx.lineTo(p.x+branch.dx,p.y+branch.dy);ctx.stroke();
                        if(pass===3) {ctx.lineWidth=0.6*effect.scaleFactor;ctx.beginPath();ctx.moveTo(p.x+branch.dx*0.5,p.y+branch.dy*0.55);ctx.lineTo(p.x+branch.dx*0.45-7*effect.scaleFactor,p.y+branch.dy*0.8);ctx.stroke()}
                    }
                }
            }
        }
    }
    Timer { interval: 55; repeat: true; running: effect.animating; onTriggered: effect.phase+=0.7 }
    ParallelAnimation {
        id: strike
        NumberAnimation { target: effect; property: 'reveal'; from: 0; to: 1; duration: 180; easing.type: Easing.OutCubic }
        SequentialAnimation {
            NumberAnimation { target: effect; property: 'glow'; from: 0; to: 1; duration: effect.durationSeconds*1000*0.08; easing.type: Easing.OutQuad }
            PauseAnimation { duration: effect.durationSeconds*1000*0.56 }
            NumberAnimation { target: effect; property: 'glow'; to: 0; duration: effect.durationSeconds*1000*0.36; easing.type: Easing.InOutQuad }
        }
        onFinished: effect.schedule()
    }
    Component.onCompleted: { if(effectEnabled) {cadence.interval=3500;cadence.restart()} }
    Timer { id: cadence; interval: 3500; running: effect.effectEnabled; onTriggered: effect.trigger() }
}
