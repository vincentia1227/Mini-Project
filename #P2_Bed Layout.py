"""
Title : Bed layout

"""


import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import System
import math

a = []

ghdoc = sc.doc
sc.doc = Rhino.RhinoDoc.ActiveDoc

try:
    if isinstance(block, System.Guid):
        block_obj = sc.doc.Objects.Find(block)
        block = block_obj.Geometry
    if isinstance(curve, System.Guid):
        curve = sc.doc.Objects.Find(curve).Geometry
    
    if block and curve and spacing > 0:
        
        block_geoms = []
        if isinstance(block, rg.InstanceReferenceGeometry):
            parent_id = block.ParentIdefId
            idef = sc.doc.InstanceDefinitions.FindId(parent_id)
            if idef:
                block_objects = idef.GetObjects()
                block_geoms = [obj.Geometry.Duplicate() for obj in block_objects]
        else:
            block_geoms = [block]

        base_brep = block_geoms[0] if block_geoms else block
        bbox = base_brep.GetBoundingBox(True)
        min_pt = bbox.Min
        max_pt = bbox.Max
        min_z = min_pt.Z

        x_length = max_pt.X - min_pt.X
        y_length = max_pt.Y - min_pt.Y

        if isinstance(base_brep, rg.Brep):
            for face in base_brep.Faces:
                face_bbox = face.GetBoundingBox(True)
                if abs(face_bbox.Min.Z - min_z) < 0.01 and abs(face_bbox.Max.Z - min_z) < 0.01:
                    x_length = face_bbox.Max.X - face_bbox.Min.X
                    y_length = face_bbox.Max.Y - face_bbox.Min.Y
                    break

        long_length = max(x_length, y_length)
        short_length = min(x_length, y_length)
        half_long = long_length / 2

        is_closed = curve.IsClosed

        base_pt = rg.Point3d(
            (min_pt.X + max_pt.X) / 2,
            (min_pt.Y + max_pt.Y) / 2,
            min_pt.Z
        )

        source_plane = rg.Plane.WorldXY
        source_plane.Origin = base_pt

        curve_length = curve.GetLength()

        if is_closed:
            start_dist = 0
            end_dist = curve_length
        else:
            start_dist = half_long
            end_dist = curve_length - half_long

        if start_dist > end_dist:
            print("❌ 커브가 너무 짧아서 블록 배치 불가!")
        else:
            placed_bboxes = []
            placed_geoms_list = []

            distance = start_dist
            while distance < end_dist if is_closed else distance <= end_dist:
                success, t = curve.LengthParameter(distance)
                
                if success:
                    point_on_curve = curve.PointAt(t)

                    tangent = curve.TangentAt(t)
                    tangent.Z = 0
                    tangent.Unitize()

                    normal = rg.Vector3d.CrossProduct(rg.Vector3d.ZAxis, tangent)
                    normal.Unitize()

                    target_plane = rg.Plane(
                        point_on_curve,
                        normal,
                        rg.Vector3d.CrossProduct(normal, rg.Vector3d.ZAxis) * -1
                    )

                    transform = rg.Transform.PlaneToPlane(source_plane, target_plane)

                    # 열린 커브일 때 안쪽으로 이동
                    if not is_closed and offset_into_curve is not None:
                        direction = -normal if flip else normal
                        move_transform = rg.Transform.Translation(direction * offset_into_curve)

                    current_geoms = []
                    current_bbox = rg.BoundingBox.Empty
                    for geom in block_geoms:
                        new_geom = geom.Duplicate()
                        new_geom.Transform(transform)
                        if not is_closed and offset_into_curve is not None:
                            new_geom.Transform(move_transform)
                        current_geoms.append(new_geom)
                        current_bbox.Union(new_geom.GetBoundingBox(True))

                    is_overlapping = False
                    for prev_bbox in placed_bboxes:
                        intersection = rg.BoundingBox(
                            rg.Point3d(
                                max(current_bbox.Min.X, prev_bbox.Min.X),
                                max(current_bbox.Min.Y, prev_bbox.Min.Y),
                                max(current_bbox.Min.Z, prev_bbox.Min.Z)
                            ),
                            rg.Point3d(
                                min(current_bbox.Max.X, prev_bbox.Max.X),
                                min(current_bbox.Max.Y, prev_bbox.Max.Y),
                                min(current_bbox.Max.Z, prev_bbox.Max.Z)
                            )
                        )
                        if intersection.IsValid:
                            is_overlapping = True
                            break

                    if not is_overlapping:
                        placed_bboxes.append(current_bbox)
                        placed_geoms_list.append(current_geoms)

                distance += spacing

            for geoms in placed_geoms_list:
                for geom in geoms:
                    a.append(geom)

finally:
    sc.doc = ghdoc