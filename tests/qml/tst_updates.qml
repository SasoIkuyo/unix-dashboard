import QtQuick
import QtTest
TestCase {
    name: 'DashboardUpdates'
    function test_stableDelegatesAndAnimation() {
        let component=Qt.createComponent(Qt.resolvedUrl('../../Desktop.qml'));
        compare(component.status,Component.Ready,component.errorString());
        let d=component.createObject(null,{visible:false,endpoint:'http://127.0.0.1:1'});
        verify(d!==null);
        let sample={clock:'12:00',theme:'Lavanda',gauges:[{value:10,text:'10%',label:'CPU',detail:'test'}],therms:[{sensor:'CPU',value:40,low:39,high:42}],days:[{day:21,current:true,today:true,value:10,duration:'10s'}],weekDays:[{label:'MIÉ',seconds:10,duration:'10s'}],apps:[],appsWeek:[],cpuHistory:[40,41],gpuHistory:[]};
        d.metrics=sample; wait(1000);
        let repeaters=['gauges','therms','days','weekDays'].map(n=>findChild(d,n+'Repeater'));
        let before=repeaters.map(r=>r.itemAt(0));
        let ring=findChild(before[0],'gaugeRing'); compare(Math.round(ring.amount),10);
        let updated=JSON.parse(JSON.stringify(sample));updated.gauges[0].value=90;updated.gauges[0].text='90%';updated.cpuHistory=[40,41,45];
        d.metrics=updated; wait(150);
        for(let i=0;i<repeaters.length;i++)compare(repeaters[i].itemAt(0),before[i],'Delegate must survive refresh');
        verify(ring.amount>10 && ring.amount<90,'Gauge interpolates instead of jumping');
        wait(950);compare(Math.round(ring.amount),90);
        d.destroy();
    }
    function test_weatherForecastPersistsAcrossRefresh() {
        let component=Qt.createComponent(Qt.resolvedUrl('../../Desktop.qml'));
        let d=component.createObject(null,{visible:false,endpoint:'http://127.0.0.1:1'});
        let forecast=Array.from({length:5},(_,i)=>({day:'Día '+i,icon:'☀',high:22,low:10,rain:5}));
        let sample={weather:{ready:true,city:'Ciudad de prueba',temperature:20,status:'Despejado',icon:'☀',feels:19,humidity:45,wind:10,updated:'12:00',forecast:forecast}};
        d.metrics=sample;wait(50);
        let r=findChild(d,'weatherRepeater');compare(r.count,5);let first=r.itemAt(0);
        let update=JSON.parse(JSON.stringify(sample));update.weather.temperature=21;update.weather.forecast[0].high=23;
        d.metrics=update;wait(50);compare(r.itemAt(0),first);compare(first.day.high,23);
        d.destroy();
    }

    function test_preferencesPopup() {
        let component=Qt.createComponent(Qt.resolvedUrl('../../Desktop.qml'));
        compare(component.status,Component.Ready,component.errorString());
        let d=component.createObject(null,{visible:true,endpoint:'http://127.0.0.1:1'});
        d.preferences={theme:'Obsidiana',lightningMin:3,lightningMax:6,fanMode:'Automático'};
        let popup=findChild(d,'preferencesDialog');verify(popup!==null);
        popup.open();wait(300);verify(popup.visible);
        compare(findChild(popup,'settingsTheme').currentText,'Obsidiana');
        compare(findChild(popup,'settingsMinimum').value,3);
        compare(findChild(popup,'settingsMaximum').value,6);
        let fans=findChild(popup,'fanProfilesEditor');
        compare(fans.values().fanMode,'Automático');verify(!fans.controlReady);
        fans.setPoint(0,70);let curve=fans.values().fanProfiles.Silencioso;verify(curve[1]>=curve[0]);
        popup.close();verify(!popup.visible);d.destroy();
    }

    function test_allCardsFit() {
        let component=Qt.createComponent(Qt.resolvedUrl('../../Desktop.qml'));compare(component.status,Component.Ready,component.errorString());
        let d=component.createObject(null,{visible:false,width:968,height:1858,endpoint:'http://127.0.0.1:1'});
        d.metrics={gauges:Array.from({length:4},()=>({value:25,text:'25%',label:'CPU',detail:'16 hilos'})),therms:Array.from({length:6},()=>({sensor:'CPU',value:45,low:40,high:50})),days:Array.from({length:35},(_,i)=>({day:i%31+1,current:true,today:false,value:0,duration:'0s'})),weekDays:Array.from({length:7},()=>({label:'LUN',seconds:100,duration:'1m'})),history30:Array(30).fill(0),apps:[],appsWeek:[]};
        wait(100);
        let cards=[];
        function visit(item) {if(item.objectName==='dashboardPanel')cards.push(item);for(let child of item.children || [])visit(child)}
        visit(d.contentItem);compare(cards.length,9);
        let bounds=cards.map(c=>({p:c.mapToItem(d.contentItem,0,0),w:c.width,h:c.height}));
        for(let r of bounds) {verify(r.p.x>=0 && r.p.y>=0);verify(r.p.x+r.w<=d.width+1);verify(r.p.y+r.h<=d.height+1,'Every card is visible without scroll')}
        for(let i=0;i<bounds.length;i++)for(let j=i+1;j<bounds.length;j++) {let a=bounds[i],b=bounds[j];verify(a.p.x+a.w<=b.p.x+1 || b.p.x+b.w<=a.p.x+1 || a.p.y+a.h<=b.p.y+1 || b.p.y+b.h<=a.p.y+1,'Cards must not overlap')}
        d.destroy();
    }

}
