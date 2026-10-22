import QtQuick
import QtTest
TestCase {
    name: 'LightingControls'
    function test_sliderSurvivesTelemetryRefresh() {
        let c=Qt.createComponent(Qt.resolvedUrl('../../LightingPanel.qml'));compare(c.status,Component.Ready,c.errorString());
        let p=c.createObject(null,{width:450,height:230});
        p.lightingInfo={mode:'Arcoíris',target:'Ambos',color:'00FF00',speed:81};compare(p.selectedSpeed,81);
        let slider=findChild(p,'lightingSpeed');verify(slider!==null);slider.value=23;slider.moved();compare(p.selectedSpeed,23);
        p.lightingInfo={mode:'Arcoíris',target:'Ambos',color:'00FF00',speed:81};compare(p.selectedSpeed,23);
        p.selectedMode='Respiración';p.previewColor='#2080ff';
        p.lightingInfo={mode:'Arcoíris',target:'Ambos',color:'00FF00',speed:81};compare(p.selectedMode,'Respiración');compare(p.previewColor.toString(),'#2080ff');p.destroy();
    }
    function test_liveEffectPreview() {
        let c=Qt.createComponent(Qt.resolvedUrl('../../PcCooling.qml'));compare(c.status,Component.Ready,c.errorString());
        let p=c.createObject(null,{width:300,height:280,animate:false});
        p.lightingMode='Arcoíris';let previous=p.effectColor.toString();p.effectTime=.5;verify(previous!==p.effectColor.toString());
        p.lightingMode='Apagado';compare(p.lightOpacity,0);
        p.lightingMode='Respiración';p.effectTime=.25;let high=p.lightOpacity;p.effectTime=.75;verify(p.lightOpacity<high);p.destroy();
    }
}
