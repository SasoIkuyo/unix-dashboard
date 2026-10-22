import QtQuick
import QtQuick3D.Helpers
import "MeshData.js" as MeshData
ProceduralMesh {
 positions: MeshData.data.tube_b.p.map(v=>Qt.vector3d(v[0],v[1],v[2]))
 normals: MeshData.data.tube_b.n.map(v=>Qt.vector3d(v[0],v[1],v[2]))
 indexes: MeshData.data.tube_b.i
}
