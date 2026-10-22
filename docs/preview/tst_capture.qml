import QtQuick
import QtTest

TestCase {
    name: "DocumentationPreview"

    function test_dashboardCapture() {
        const component = Qt.createComponent(Qt.resolvedUrl("../../Desktop.qml"));
        compare(component.status, Component.Ready, component.errorString());
        const dashboard = component.createObject(null, {
            visible: true, width: 968, height: 1858,
            endpoint: "http://127.0.0.1:1", selectedTheme: "Lavanda",
            preferences: {backgroundOpacity: 1, cardOpacity: 1, lightningEnabled: false}
        });
        verify(dashboard !== null);
        dashboard.metrics = {
            clock: "18:42", seconds: "08", date: "JUEVES 22 DE OCTUBRE", week: 43,
            weekday: 3, weekDates: [19, 20, 21, 22, 23, 24, 25], yearProgress: "81%",
            month: "OCTUBRE 2026", day: 22, monthDays: 31,
            weather: {ready: true, city: "Santiago", temperature: 23, status: "Despejado", icon: "☀", feels: 22, humidity: 42, wind: 12, updated: "18:40",
                forecast: [{day: "VIE", icon: "☀", high: 25, low: 12, rain: 0}, {day: "SÁB", icon: "☀", high: 26, low: 13, rain: 0}, {day: "DOM", icon: "☁", high: 22, low: 11, rain: 10}, {day: "LUN", icon: "☀", high: 24, low: 12, rain: 0}, {day: "MAR", icon: "☀", high: 25, low: 13, rain: 0}]},
            gauges: [{value: 24, text: "24%", label: "CPU", detail: "16 hilos"}, {value: 38, text: "38%", label: "RAM", detail: "12,2 / 32 GB"}, {value: 31, text: "31%", label: "GPU", detail: "4,1 / 12 GB"}, {value: 46, text: "46%", label: "DISCO", detail: "460 GB / 1 TB"}],
            therms: [{sensor: "CPU", value: 46, low: 35, high: 62}, {sensor: "GPU", value: 42, low: 32, high: 58}, {sensor: "NVMe", value: 37, low: 30, high: 44}, {sensor: "Placa", value: 34, low: 28, high: 39}],
            cpuHistory: Array.from({length: 90}, (_, i) => Math.round(44 + 4 * Math.sin(i / 7) + 2 * Math.sin(i / 3))),
            gpuHistory: Array.from({length: 90}, (_, i) => Math.round(39 + 3 * Math.sin(i / 8) + 2 * Math.sin(i / 4))),
            uptime: "7h 24m", session: "3h 18m", today: "5h 42m", total: "86h 30m", monthAverage: "4h 48m", streak: 8, activeDays: 18, bestDay: "7h 15m",
            history30: [2, 3, 4, 5, 4, 2, 6, 3, 5, 4, 6, 4, 5, 6, 3, 4, 5, 7, 4, 6, 5, 4, 3, 5, 6, 4, 5, 6, 5, 4], historyMaximum: "7h 15m", historyAverage: "4h 48m",
            days: Array.from({length: 35}, (_, i) => ({day: i < 3 ? 28 + i : i - 2, current: i >= 3 && i < 34, today: i === 24, value: i < 24 ? (i % 6 + 1) * 6000 : 0, duration: "4h 48m"})),
            weekDays: ["VIE", "SÁB", "DOM", "LUN", "MAR", "MIÉ", "JUE"].map((label, i) => ({label, seconds: 9000 + i * 1700, duration: (3 + i % 3) + "h 20m"})),
            apps: [{name: "Firefox", icon: "firefox", seconds: 7200, duration: "2h 00m"}, {name: "VS Code", icon: "code", seconds: 5400, duration: "1h 30m"}, {name: "Terminal", icon: "terminal", seconds: 3600, duration: "1h 00m"}],
            appsWeek: [{name: "VS Code", seconds: 36000, duration: "10h 00m"}, {name: "Firefox", seconds: 28800, duration: "8h 00m"}, {name: "Terminal", seconds: 14400, duration: "4h 00m"}],
            registered: "4h 30m", idle: "1h 12m", appCount: 3, cpuName: "AMD Ryzen · 8 núcleos", ramTotal: "32 GB", host: "workstation", kernel: "Linux · Hyprland"
        };
        wait(1400);
        const image = grabImage(dashboard.contentItem);
        image.save(Qt.resolvedUrl("../dashboard.png").toString().replace("file://", ""));
        dashboard.destroy();
    }
}
