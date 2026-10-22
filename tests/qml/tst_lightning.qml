import QtQuick
import QtTest
TestCase {
    name: 'LightningEffect'
    function test_strikeAndDisable() {
        let component=Qt.createComponent(Qt.resolvedUrl('../../Lightning.qml'));
        compare(component.status,Component.Ready,component.errorString());
        let effect=component.createObject(null,{width:968,height:1858});
        effect.trigger();verify(effect.animating);compare(effect.paths.length,4);
        for(let path of effect.paths) {compare(path.points.length,49);verify(path.branches.length>0);}
        for(let path of effect.paths)for(let point of path.points)verify(point.x>=0 && point.x<=968 && point.y>=0 && point.y<=1858);
        wait(180);verify(effect.glow>0);tryCompare(effect,'reveal',1,500);
        tryCompare(effect,'animating',false,2000);compare(effect.glow,0);
        effect.trigger();effect.effectEnabled=false;wait(30);
        verify(!effect.animating);compare(effect.glow,0);
        effect.trigger();verify(!effect.animating);
        effect.destroy();
    }
}
