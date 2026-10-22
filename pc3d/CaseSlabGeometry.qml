import QtQuick
import QtQuick3D.Helpers
import "MeshData.js" as MeshData
ProceduralMesh {
 positions: MeshData.data.case_slab.p.map(v=>Qt.vector3d(v[0],v[1],v[2]))
 normals: MeshData.data.case_slab.n.map(v=>Qt.vector3d(v[0],v[1],v[2]))
 indexes: MeshData.data.case_slab.i
}
