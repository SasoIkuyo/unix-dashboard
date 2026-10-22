pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
import QtQuick3D
import "pc3d" as Meshes

Item {
    id: pc
    property color accent: '#ae96ef'
    property color ink: '#e7e6ed'
    property color muted: '#9da4b2'
    property real cpuRpm: 0
    property real gpuRpm: 0
    property bool animate: true
    property real animationTime: 0
    Timer {
        interval: 42; repeat: true
        running: pc.animate && pc.visible && (!pc.Window.window || pc.Window.window.visibility !== Window.Minimized)
        onTriggered: pc.animationTime += interval / 1000
    }
    property real yaw: -24
    property real pitch: -5
    View3D {
        id: view; anchors.fill: parent
        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Transparent
            antialiasingMode: SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.Medium
            tonemapMode: SceneEnvironment.TonemapModeFilmic
        }
        PerspectiveCamera { id: sceneCamera; position: Qt.vector3d(0,120,750); eulerRotation.x: -9; fieldOfView: 32; clipNear: 1; clipFar: 2500 }
        camera: sceneCamera
        DirectionalLight { eulerRotation: Qt.vector3d(-35,-30,0); brightness: 1.6; ambientColor: '#68738a'; castsShadow: false }
        DirectionalLight { eulerRotation: Qt.vector3d(10,145,0); brightness: 0.75; color: '#b9d4ff' }
        PointLight { position: Qt.vector3d(-130,40,160); color: pc.accent; brightness: 1.5; quadraticFade: 0.5; linearFade: 0.1 }
        Node {
            id: rig; eulerRotation: Qt.vector3d(pc.pitch,pc.yaw,0); y: -5
            Meshes.RingGeometry { id: ringGeometry }
            Meshes.FrameGeometry { id: frameGeometry }
            Meshes.CaseSlabGeometry { id: caseSlab }
            Meshes.BladeGeometry { id: bladeGeometry }
            Meshes.TubeAGeometry { id: tubeA }
            Meshes.TubeBGeometry { id: tubeB }
            PrincipledMaterial { id: white; baseColor: '#e2e6ee'; roughness: 0.38; metalness: 0.3; cullMode: Material.NoCulling }
            PrincipledMaterial { id: dark; baseColor: '#141923'; roughness: 0.5; metalness: 0.2; cullMode: Material.NoCulling }
            PrincipledMaterial { id: board; baseColor: '#475367'; roughness: 0.7 }
            PrincipledMaterial { id: alloy; baseColor: '#899bb3'; metalness: 0.65; roughness: 0.25 }
            PrincipledMaterial { id: rubber; baseColor: '#bcc5d5'; roughness: 0.9; cullMode: Material.NoCulling }
            PrincipledMaterial { id: rgb; baseColor: pc.accent; emissiveFactor: Qt.vector3d(pc.accent.r*1.2,pc.accent.g*1.2,pc.accent.b*1.2); roughness: 0.25; cullMode: Material.NoCulling }
            // HYTE Y70 inspired panoramic chassis and its signature bevelled glass corner.
            // White panoramic chassis with open corner, rear tray and mesh floor.
            Model { geometry: caseSlab; position: Qt.vector3d(0,-180,0); materials: white }
            Model { geometry: caseSlab; position: Qt.vector3d(0,180,0); materials: white }
            Model { source: '#Cube'; position: Qt.vector3d(0,0,-102); scale: Qt.vector3d(3.12,3.5,0.08); materials: white }
            Model { source: '#Cube'; position: Qt.vector3d(-154,0,-10); scale: Qt.vector3d(0.08,3.5,1.9); materials: white }
            Model { source: '#Cube'; position: Qt.vector3d(154,0,49); scale: Qt.vector3d(0.055,3.55,0.055); materials: white }
            Model { source: '#Cube'; position: Qt.vector3d(-153,0,99); scale: Qt.vector3d(0.055,3.55,0.055); materials: white }
            Model { source: '#Cube'; position: Qt.vector3d(-25,-184,103); scale: Qt.vector3d(2.6,0.06,0.07); materials: alloy }
            Model { source: '#Cube'; position: Qt.vector3d(-25,182,103); scale: Qt.vector3d(2.6,0.045,0.06); materials: alloy }
            Repeater3D { model: 17
                Model { required property int index; source: '#Cube'; position: Qt.vector3d(-140+index*17,-170,0); scale: Qt.vector3d(0.025,0.015,1.9); materials: alloy }
            }
            Model { source: '#Rectangle'; position: Qt.vector3d(61,-179,108); scale: Qt.vector3d(0.49,0.075,1)
                materials: DefaultMaterial { lighting: DefaultMaterial.NoLighting; diffuseMap: Texture { sourceItem: Rectangle { width: 256; height: 48; color: '#dce2eb'; Text { anchors.centerIn: parent; text: 'HYTE Y70'; color: '#47546b'; font.pixelSize: 31; font.bold: true } } } }
            }
            // Radiator and its three fans across the ceiling.
            Model { source: '#Cube'; position: Qt.vector3d(-5,160,-4); scale: Qt.vector3d(2.9,0.22,0.95); materials: dark }
            Repeater3D { model: 3
                Fan { required property int index; x: -99+index*96; y: 144; z: -4; eulerRotation.x: 90; size: 39; rpm: pc.cpuRpm }
            }
            // White Pro RS board, heatsinks, socket and two illuminated RAM sticks.
            Model { source: '#Cube'; position: Qt.vector3d(-29,22,-85); scale: Qt.vector3d(1.98,2.30,0.07); materials: board }
            Model { source: '#Cube'; position: Qt.vector3d(-37,111,-72); scale: Qt.vector3d(1.38,0.26,0.18); materials: white }
            Model { source: '#Cube'; position: Qt.vector3d(-113,45,-70); scale: Qt.vector3d(0.29,1.05,0.21); materials: white }
            Repeater3D { model: 7
                Model { required property int index; source: '#Cube'; position: Qt.vector3d(-123+index*3.5,46,-58); scale: Qt.vector3d(0.009,0.96,0.008); materials: alloy }
            }
            Repeater3D { model: 2
                Node { required property int index; x: 38+index*16; y: 46; z: -65
                    Model { source: '#Cube'; scale: Qt.vector3d(0.10,0.98,0.17); materials: white }
                    Model { source: '#Cube'; z: 10; scale: Qt.vector3d(0.055,0.95,0.025); materials: rgb }
                }
            }
            Fan { x: -25; y: 37; z: -37; size: 32; rpm: pc.cpuRpm; isPump: true }
            Model { geometry: tubeA; materials: rubber }
            Model { geometry: tubeB; materials: rubber }
            // Three lateral case fans, rear exhaust, and two bottom fans.
            Repeater3D { model: 3
                Fan { required property int index; x: 107; y: 96-index*91; z: -54; size: 36; rpm: 700; illustrative: true }
            }
            Fan { x: -144; y: 65; z: 0; eulerRotation.y: 90; size: 35; rpm: 700; illustrative: true }
            Repeater3D { model: 2
                Fan { required property int index; x: -60+index*101; y: -163; z: 18; eulerRotation.x: -90; size: 39; rpm: 700; illustrative: true }
            }
            // Vertically mounted dark RTX card with three visible cooler fans.
            Model { source: '#Cube'; position: Qt.vector3d(-19,-100,48); scale: Qt.vector3d(2.32,0.81,0.37); materials: dark }
            Model { source: '#Cube'; position: Qt.vector3d(-19,-57,48); scale: Qt.vector3d(2.34,0.05,0.39); materials: alloy }
            Repeater3D { model: 3
                Fan { required property int index; x: -99+index*78; y: -100; z: 70; size: 28; rpm: pc.gpuRpm; gpuStyle: true }
            }
            Model { source: '#Rectangle'; position: Qt.vector3d(-34,-61,70); scale: Qt.vector3d(1.4,0.13,1)
                materials: DefaultMaterial { lighting: DefaultMaterial.NoLighting; diffuseMap: Texture { sourceItem: Rectangle { width: 512; height: 64; color: '#18212d'; Text { anchors.centerIn: parent; text: 'GEFORCE RTX'; color: '#e9edf5'; font.pixelSize: 42; font.bold: true } } } }
            }
            Model { source: '#Cube'; position: Qt.vector3d(0,-170,98); scale: Qt.vector3d(2.9,0.018,0.025); materials: rgb }
            // Small chibi collectible with spiky white hair, matching the case photos.
            Node { position: Qt.vector3d(119,-152,65); scale: Qt.vector3d(0.7,0.7,0.7)
                Model { source: '#Cylinder'; y: -24; scale: Qt.vector3d(0.30,0.035,0.30); materials: dark }
                Model { source: '#Cube'; y: -10; scale: Qt.vector3d(0.12,0.22,0.10); materials: board }
                Model { source: '#Sphere'; y: 9; scale: Qt.vector3d(0.25,0.25,0.23); materials: white }
                Repeater3D { model: 7
                    Model { required property int index; source: '#Cone'; x: Math.cos(index*0.9)*9; y: 18+Math.sin(index*0.9)*4; z: Math.sin(index*0.9)*6; eulerRotation.z: (index-3)*17; scale: Qt.vector3d(0.095,0.17,0.09); materials: white }
                }
                Model { source: '#Sphere'; position: Qt.vector3d(-4,10,11); scale: Qt.vector3d(0.025,0.045,0.025); materials: dark }
                Model { source: '#Sphere'; position: Qt.vector3d(4,10,11); scale: Qt.vector3d(0.025,0.045,0.025); materials: dark }
            }
            // Low-opacity glass preserves the view of the hardware.
            Model { source: '#Cube'; position: Qt.vector3d(-23,0,105); scale: Qt.vector3d(2.55,3.48,0.008)
                materials: PrincipledMaterial { baseColor: '#ffffff'; baseColorMap: Texture { source: 'pc3d/glass-mask.svg' } alphaMode: PrincipledMaterial.Blend; roughness: 0.17; metalness: 0.05; cullMode: Material.NoCulling }
            }
            Model { source: '#Cube'; position: Qt.vector3d(130,0,78); eulerRotation.y: 44; scale: Qt.vector3d(0.78,3.48,0.008)
                materials: PrincipledMaterial { baseColor: '#ffffff'; baseColorMap: Texture { source: 'pc3d/glass-mask.svg' } alphaMode: PrincipledMaterial.Blend; roughness: 0.17; cullMode: Material.NoCulling }
            }
            component Fan: Node {
                id: fan
                property real size: 35
                property real rpm: 0
                property bool gpuStyle: false
                property bool isPump: false
                property bool illustrative: false
                Model { geometry: frameGeometry; scale: Qt.vector3d(fan.size,fan.size,fan.size*0.6); materials: fan.gpuStyle ? dark : white; visible: !fan.isPump }
                Model { source: '#Cylinder'; z: -fan.size*0.2; eulerRotation.x: 90; scale: Qt.vector3d(fan.size*0.024,fan.size*0.004,fan.size*0.024); materials: white; visible: fan.isPump }
                Model { geometry: ringGeometry; z: fan.size*0.08; scale: Qt.vector3d(fan.size*0.96,fan.size*0.96,fan.size*0.96); materials: rgb }
                Node { id: rotor; z: fan.size*0.08; property real angle: fan.rpm > 0 ? (pc.animationTime * 360000 / Math.max(900,Math.min(6000,1800000/Math.max(1,fan.rpm)))) % 360 : 0; eulerRotation.z: angle
                    Repeater3D { model: 7
                        Model { required property int index; geometry: bladeGeometry; eulerRotation.z: index*360/7; scale: Qt.vector3d(fan.size,fan.size,fan.size); materials: fan.gpuStyle ? alloy : white }
                    }
                }
                Model { source: '#Cylinder'; eulerRotation.x: 90; z: fan.size*0.14; scale: Qt.vector3d(fan.size*0.005,fan.size*0.002,fan.size*0.005); materials: fan.gpuStyle ? dark : alloy }
            }
        }
    }
}
