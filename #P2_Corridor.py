"""
Title : Corridor

"""



import Rhino.Geometry as rg
import scriptcontext as sc
import System

surfaces = []
split_curves_out = []
oc1 = None
oc2 = None

# GUID 변환
if isinstance(curve, System.Guid):
    curve_obj = sc.doc.Objects.Find(curve)
    curve = curve_obj.Geometry

if isinstance(rail, System.Guid):
    rail_obj = sc.doc.Objects.Find(rail)
    rail = rail_obj.Geometry

if curve is not None and offset_distance is not None and offset_distance > 0:

    tol = sc.doc.ModelAbsoluteTolerance

    offset_crv1 = curve.Offset(
        rg.Plane.WorldXY,
        offset_distance,
        tol,
        rg.CurveOffsetCornerStyle.Sharp
    )

    offset_crv2 = curve.Offset(
        rg.Plane.WorldXY,
        -offset_distance,
        tol,
        rg.CurveOffsetCornerStyle.Sharp
    )

    if offset_crv1 and offset_crv2:
        oc1 = offset_crv1[0]
        oc2 = offset_crv2[0]

        loft_brep = None
        loft = rg.Brep.CreateFromLoft(
            [oc1, oc2],
            rg.Point3d.Unset,
            rg.Point3d.Unset,
            rg.LoftType.Straight,
            False
        )

        if loft:
            for srf in loft:
                surfaces.append(srf)
                loft_brep = srf

        if rail:
            split_params = []

            ix1 = rg.Intersect.Intersection.CurveCurve(rail, oc1, tol, tol)
            for ix in ix1:
                split_params.append(ix.ParameterA)

            ix2 = rg.Intersect.Intersection.CurveCurve(rail, oc2, tol, tol)
            for ix in ix2:
                split_params.append(ix.ParameterA)

            if split_params:
                split_params.sort()
                split_result = rail.Split(split_params)

                if split_result and len(split_result) > 0:
                    for seg in split_result:
                        mid_t = (seg.Domain.Min + seg.Domain.Max) / 2
                        mid_pt = seg.PointAt(mid_t)

                        is_inside = False
                        if loft_brep:
                            closest_pt = loft_brep.ClosestPoint(mid_pt)
                            dist = mid_pt.DistanceTo(closest_pt)
                            if dist <= tol * 10:
                                is_inside = True

                        if not is_inside:
                            split_curves_out.append(seg)
                else:
                    split_curves_out.append(rail)
            else:
                split_curves_out.append(rail)

a = None         # 비움
b = oc1          # 오프셋 커브 1
c = oc2          # 오프셋 커브 2
d = surfaces     # Loft 면
e = split_curves_out  # 분할된 rail 세그먼트