"""
Title : NS(Nurse Station)
Grasshopper Python Script Component
=====================================
Inputs:
    curve           : Curve  - 기준 커브
    offset_distance : float  - 오프셋 거리
    extrude_height  : float  - 압출 높이
    flip            : bool   - True=바깥쪽, False=안쪽 오프셋
    solid_length    : float  - 솔리드 길이 (최대 = curve 길이)
    center_point    : Point3d - 솔리드 길이의 중심이 될 커브 위의 점

Outputs:
    a : 원래 커브 + 선택된 오프셋 커브
    b : 바닥 Loft 면
    c : Extrude 결과 Solid
"""

import Rhino.Geometry as rg
import scriptcontext as sc
import System

def unwrap(val):
    if isinstance(val, (list, tuple)):
        return val[0] if len(val) > 0 else None
    return val

surfaces          = []
offset_curves_out = []
extrude_breps     = []

# ── GUID 변환 ─────────────────────────────────────────────────
_curve        = unwrap(curve)
_offset_dist  = unwrap(offset_distance)
_height       = unwrap(extrude_height)
_flip         = unwrap(flip)
_length       = unwrap(solid_length)
_center_pt    = unwrap(center_point)

if isinstance(_curve, System.Guid):
    obj = sc.doc.Objects.Find(_curve)
    if obj: _curve = obj.Geometry

if _curve is not None and _offset_dist is not None and _height is not None:

    tol          = sc.doc.ModelAbsoluteTolerance
    curve_length = _curve.GetLength()

    # ── solid_length 클램프 ───────────────────────────────────
    if _length is None:
        _length = curve_length
    else:
        _length = max(0.001, min(float(_length), curve_length))

    print("curve_length={:.3f}  solid_length={:.3f}".format(curve_length, _length))

    # ── 중심점 → 커브 위 파라미터 t_center 계산 ─────────────
    if _center_pt is not None:
        # 커브에서 center_point에 가장 가까운 파라미터
        cp_result = _curve.ClosestPoint(_center_pt)
        t_center  = cp_result[1]
        # t_center 위치까지의 커브 길이
        len_to_center = _curve.GetLength(
            rg.Interval(_curve.Domain.Min, t_center))
        print("center_point 커브 길이 위치: {:.3f}".format(len_to_center))
    else:
        # center_point 없으면 커브 시작점 기준 (기존 동작)
        len_to_center = _length / 2.0
        print("center_point 없음 → 시작점 기준")

    # ── 중심 기준으로 앞뒤 half만큼 트림 구간 계산 ───────────
    half        = _length / 2.0
    len_start   = len_to_center - half   # 트림 시작 길이
    len_end     = len_to_center + half   # 트림 끝 길이

    # 커브 범위 클램프
    len_start   = max(0.0, len_start)
    len_end     = min(curve_length, len_end)

    crv_domain  = _curve.Domain

    # 길이 → t 파라미터 변환
    t_start_result = _curve.LengthParameter(len_start) if len_start > 0 else (True, crv_domain.Min)
    t_end_result   = _curve.LengthParameter(len_end)   if len_end < curve_length else (True, crv_domain.Max)

    if t_start_result[0] and t_end_result[0]:
        t_start = t_start_result[1]
        t_end   = t_end_result[1]
        working_curve = _curve.Trim(t_start, t_end)
        if working_curve is None:
            print("Warning: Trim 실패, 원본 커브 사용")
            working_curve = _curve
        else:
            print("트림 완료: {:.3f} ~ {:.3f}".format(len_start, len_end))
    else:
        print("Warning: LengthParameter 실패, 원본 커브 사용")
        working_curve = _curve

    # ── +/- 방향 오프셋 ──────────────────────────────────────
    offset_crv1 = working_curve.Offset(
        rg.Plane.WorldXY, _offset_dist, tol, rg.CurveOffsetCornerStyle.Sharp)
    offset_crv2 = working_curve.Offset(
        rg.Plane.WorldXY, -_offset_dist, tol, rg.CurveOffsetCornerStyle.Sharp)

    selected_crv = None
    if offset_crv1 and offset_crv2:
        oc1 = offset_crv1[0]
        oc2 = offset_crv2[0]

        oc1_bbox = oc1.GetBoundingBox(True)
        oc2_bbox = oc2.GetBoundingBox(True)
        oc1_size = ((oc1_bbox.Max.X - oc1_bbox.Min.X) *
                    (oc1_bbox.Max.Y - oc1_bbox.Min.Y))
        oc2_size = ((oc2_bbox.Max.X - oc2_bbox.Min.X) *
                    (oc2_bbox.Max.Y - oc2_bbox.Min.Y))

        if _flip:
            selected_crv = oc1 if oc1_size > oc2_size else oc2
        else:
            selected_crv = oc1 if oc1_size < oc2_size else oc2

    if selected_crv:
        offset_curves_out.append(working_curve)
        offset_curves_out.append(selected_crv)

        loft = rg.Brep.CreateFromLoft(
            [working_curve, selected_crv],
            rg.Point3d.Unset,
            rg.Point3d.Unset,
            rg.LoftType.Straight,
            False
        )

        if loft:
            for srf in loft:
                surfaces.append(srf)

                extrude_vec    = rg.Vector3d(0, 0, _height)
                extrude_result = srf.Faces[0].CreateExtrusion(
                    rg.LineCurve(
                        rg.Point3d(0, 0, 0),
                        rg.Point3d(0, 0, _height)
                    ),
                    True
                )

                if extrude_result:
                    extrude_breps.append(extrude_result)
                else:
                    top_srf = srf.DuplicateBrep()
                    top_srf.Transform(rg.Transform.Translation(extrude_vec))

                    all_breps = [srf, top_srf]
                    for crv in [working_curve, selected_crv]:
                        wall = rg.Surface.CreateExtrusion(crv, extrude_vec)
                        if wall:
                            all_breps.append(wall.ToBrep())

                    joined = rg.Brep.JoinBreps(all_breps, tol)
                    if joined:
                        for brep in joined:
                            extrude_breps.append(brep)

# ── Outputs ───────────────────────────────────────────────────
a = offset_curves_out
b = surfaces
c = extrude_breps
