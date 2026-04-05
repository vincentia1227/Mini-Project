"""
Title : NS Office
Grasshopper Python Script Component
=====================================
Inputs:
    curve     : Curve - 기준 커브
    thickness : float - 벽 두께 (양쪽으로 thickness/2씩 오프셋)
    height    : float - 벽 높이

Outputs:
    wall : Brep - 벽체 솔리드
"""

import Rhino.Geometry as rg
import scriptcontext as sc
import System

def unwrap(val):
    if isinstance(val, (list, tuple)):
        return val[0] if len(val) > 0 else None
    return val

_curve     = unwrap(curve)
_thickness = unwrap(thickness)
_height    = unwrap(height)

# GUID 변환
if isinstance(_curve, System.Guid):
    obj = sc.doc.Objects.Find(_curve)
    if obj: _curve = obj.Geometry

wall = None

errors = []
if _curve     is None:                    errors.append("curve")
if _thickness is None or _thickness <= 0: errors.append("thickness")
if _height    is None or _height    <= 0: errors.append("height")

if errors:
    print("Error: " + ", ".join(errors))
else:
    tol  = sc.doc.ModelAbsoluteTolerance
    half = _thickness / 2.0

    # ── 양쪽으로 thickness/2 오프셋 ─────────────────────────
    off_a = _curve.Offset(rg.Plane.WorldXY,  half, tol, rg.CurveOffsetCornerStyle.Sharp)
    off_b = _curve.Offset(rg.Plane.WorldXY, -half, tol, rg.CurveOffsetCornerStyle.Sharp)

    if not off_a or not off_b:
        print("Error: 오프셋 실패")
    else:
        crv_a = off_a[0]
        crv_b = off_b[0]

        # ── 두 커브 Loft → 바닥 면 ──────────────────────────
        loft = rg.Brep.CreateFromLoft(
            [crv_a, crv_b],
            rg.Point3d.Unset,
            rg.Point3d.Unset,
            rg.LoftType.Straight,
            False
        )

        if not loft:
            print("Error: Loft 실패")
        else:
            base_srf = loft[0]
            extrude_vec = rg.Vector3d(0, 0, _height)

            # ── 두 오프셋 커브 측면 extrude ─────────────────
            srf_a = rg.Surface.CreateExtrusion(crv_a, extrude_vec)
            srf_b = rg.Surface.CreateExtrusion(crv_b, extrude_vec)

            # ── 상단 면: base를 height만큼 이동 ─────────────
            top_srf = base_srf.DuplicateBrep()
            top_srf.Transform(rg.Transform.Translation(extrude_vec))

            # ── 끝면 2개 (커브 양 끝 마감) ──────────────────
            s_a0 = crv_a.PointAtStart;  s_b0 = crv_b.PointAtStart
            e_a0 = crv_a.PointAtEnd;    e_b0 = crv_b.PointAtEnd

            end0_crv = rg.PolylineCurve([
                s_a0,
                s_b0,
                rg.Point3d(s_b0.X, s_b0.Y, s_b0.Z + _height),
                rg.Point3d(s_a0.X, s_a0.Y, s_a0.Z + _height),
                s_a0
            ])
            end1_crv = rg.PolylineCurve([
                e_a0,
                e_b0,
                rg.Point3d(e_b0.X, e_b0.Y, e_b0.Z + _height),
                rg.Point3d(e_a0.X, e_a0.Y, e_a0.Z + _height),
                e_a0
            ])

            end0 = rg.Brep.CreatePlanarBreps(end0_crv, tol)
            end1 = rg.Brep.CreatePlanarBreps(end1_crv, tol)

            # ── 모든 면 조립 ─────────────────────────────────
            all_faces = [base_srf, top_srf]
            if srf_a: all_faces.append(srf_a.ToBrep())
            if srf_b: all_faces.append(srf_b.ToBrep())
            if end0:  all_faces += list(end0)
            if end1:  all_faces += list(end1)

            joined = rg.Brep.JoinBreps(all_faces, tol)

            if joined and len(joined) > 0:
                wall = joined[0]
                print("완료: wall IsValid={}".format(wall.IsValid))
            else:
                print("Error: JoinBreps 실패 (faces={})".format(len(all_faces)))
