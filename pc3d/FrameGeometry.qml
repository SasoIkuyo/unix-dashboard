import QtQuick
import QtQuick3D.Helpers
import "MeshData.js" as MeshData
ProceduralMesh {
 positions: MeshData.data.frame.p.map(v=>Qt.vector3d(v[0],v[1],v[2]))
 normals: MeshData.data.frame.n.map(v=>Qt.vector3d(v[0],v[1],v[2]))
 indexes: MeshData.data.frame.i
}
