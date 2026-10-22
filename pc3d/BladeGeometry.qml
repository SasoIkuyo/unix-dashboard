import QtQuick
import QtQuick3D.Helpers
import "MeshData.js" as MeshData
ProceduralMesh {
 positions: MeshData.data.blade.p.map(v=>Qt.vector3d(v[0],v[1],v[2]))
 normals: MeshData.data.blade.n.map(v=>Qt.vector3d(v[0],v[1],v[2]))
 indexes: MeshData.data.blade.i
}
