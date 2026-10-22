import QtQuick
import QtTest
TestCase {
    name: 'CoolingCard'
    function test_telemetryAndTargets() {
        let c=Qt.createComponent(Qt.resolvedUrl('../../CoolingPanel.qml'));compare(c.status,Component.Ready,c.errorString());
        let p=c.createObject(null,{width:850,height:230,endpoint:'http://127.0.0.1:1'});
        p.preferences={fanMode:'Automático',fanChannels:[],fanGPU:false};
        p.fanInfo={controlReady:true,rows:[{label:'ARCTIC',source:'Placa',rpm:900,percent:null},{label:'GPU 1',source:'NVIDIA',rpm:700,percent:30},{label:'GPU 2',source:'NVIDIA',rpm:800,percent:30},{label:'Libre',source:'Placa',rpm:0,percent:null}]};
        compare(p.cpuRpm,900);compare(p.gpuRpm,750);compare(p.rows.length,3);
        for(let name of ['Automático','Silencioso','Equilibrado','Rendimiento','Máximo'])verify(findChild(p,'mode'+name)!==null);
        p.changeMode('Silencioso');verify(p.message.length>0);verify(!p.saving);
        p.fanInfo={controlReady:true,rows:[{label:'ARCTIC',source:'Placa',rpm:1100,percent:null}]};
        compare(p.cpuRpm,1100);compare(p.gpuRpm,0);p.destroy();
    }
}
