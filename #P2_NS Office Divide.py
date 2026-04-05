"""
Title : NS Office Divide
Grasshopper Python Script Component
Inputs:
    surface        : Surface/Brep
    divisions      : int
    wall_height    : float
    wall_thickness : float
    use_v_dir      : bool - False=U방향, True=V방향

Outputs:
    walls  : DataTree[Brep]
    frames : DataTree[Curve]
"""

import Rhino.Geometry as rg
import scriptcontext as sc
import System
from Grasshopper import DataTree
from Grasshopper.Kernel.Data import GH_Path

def unwrap(val):
    if isinstance(val, (list, tuple)):
        return val[0] if len(val) > 0 else None
    return val

def extract_surface(val):
    if isinstance(val, (list, tuple)):
        val = val[0] if len(val) > 0 else None
    if val is None: return None
    if isinstance(val, System.Guid):
        obj = sc.doc.Objects.Find(val)
        val = obj.Geometry if obj else None
    if val is None: return None
    if isinstance(val, rg.Brep):
        return val.Faces[0].UnderlyingSurface() if val.Faces.Count > 0 else None
    return val  # Surface 또는 서브클래스

_srf       = extract_surface(surface)
_divisions = unwrap(divisions)
_height    = unwrap(wall_height)
_thickness = unwrap(wall_thickness)
_use_v     = unwrap(use_v_dir)
if _use_v is None: _use_v = False

walls  = DataTree[rg.Brep]()
frames = DataTree[rg.Curve]()

errors = []
if _srf       is None:                        errors.append("surface")
if _divisions is None or int(_divisions) < 1: errors.append("divisions")
if _height    is None or _height    <= 0:     errors.append("wall_height")
if _thickness is None or _thickness <= 0:     errors.append("wall_thickness")

if errors:
    print("Error: " + ", ".join(errors))
else:
    _divisions = int(_divisions)
    tol  = sc.doc.ModelAbsoluteTolerance
    half = _thickness / 2.0
    extrude_vec = rg.Vector3d(0, 0, _height)

    u_domain = _srf.Domain(0)
    v_domain = _srf.Domain(1)
    print("srf OK | U:{:.1f}~{:.1f} V:{:.1f}~{:.1f}".format(
        u_domain.Min, u_domain.Max, v_domain.Min, v_domain.Max))

    for i in range(_divisions):
        t = float(i) / float(_divisions)

        # ── 아이소커브 ───────────────────────────────────────
        if not _use_v:
            iso_crv = _srf.IsoCurve(1, u_domain.ParameterAt(t))
        else:
            iso_crv = _srf.IsoCurve(0, v_domain.ParameterAt(t))

        if iso_crv is None:
            print("구간 {}: iso None".format(i))
            continue
        frames.Add(iso_crv, GH_Path(i))

        # ── ±half 오프셋 ─────────────────────────────────────
        off_a = iso_crv.Offset(rg.Plane.WorldXY,  half, tol, rg.CurveOffsetCornerStyle.Sharp)
        off_b = iso_crv.Offset(rg.Plane.WorldXY, -half, tol, rg.CurveOffsetCornerStyle.Sharp)

        if not off_a or not off_b:
            print("구간 {}: offset 실패".format(i))
            continue

        crv_a = off_a[0]
        crv_b = off_b[0]

        # ── 오프셋 커브 2개를 위로 extrude한 서피스 2장 ─────
        srf_a = rg.Surface.CreateExtrusion(crv_a, extrude_vec)
        srf_b = rg.Surface.CreateExtrusion(crv_b, extrude_vec)

        if srf_a is None or srf_b is None:
            print("구간 {}: extrusion srf 실패".format(i))
            continue

        # ── 바닥/상단 캡 커브 생성 ───────────────────────────
        # 바닥: 두 오프셋 커브 + 양 끝 연결선
        s0 = crv_a.PointAtStart
        e0 = crv_a.PointAtEnd
        s1 = crv_b.PointAtStart
        e1 = crv_b.PointAtEnd

        cap_bot_crv = rg.PolylineCurve([s0, e0,
                                        rg.Point3d(e1.X, e1.Y, e1.Z),
                                        rg.Point3d(s1.X, s1.Y, s1.Z),
                                        s0])
        cap_top_crv = rg.PolylineCurve([
            rg.Point3d(s0.X, s0.Y, s0.Z + _height),
            rg.Point3d(e0.X, e0.Y, e0.Z + _height),
            rg.Point3d(e1.X, e1.Y, e1.Z + _height),
            rg.Point3d(s1.X, s1.Y, s1.Z + _height),
            rg.Point3d(s0.X, s0.Y, s0.Z + _height)
        ])

        cap_bot = rg.Brep.CreatePlanarBreps(cap_bot_crv, tol)
        cap_top = rg.Brep.CreatePlanarBreps(cap_top_crv, tol)

        # ── 끝면 2개 (양쪽 마감) ────────────────────────────
        end0_crv = rg.PolylineCurve([
            s0,
            rg.Point3d(s1.X, s1.Y, s1.Z),
            rg.Point3d(s1.X, s1.Y, s1.Z + _height),
            rg.Point3d(s0.X, s0.Y, s0.Z + _height),
            s0
        ])
        end1_crv = rg.PolylineCurve([
            e0,
            rg.Point3d(e1.X, e1.Y, e1.Z),
            rg.Point3d(e1.X, e1.Y, e1.Z + _height),
            rg.Point3d(e0.X, e0.Y, e0.Z + _height),
            e0
        ])
        end0 = rg.Brep.CreatePlanarBreps(end0_crv, tol)
        end1 = rg.Brep.CreatePlanarBreps(end1_crv, tol)

        # ── 모든 면 JoinBreps ────────────────────────────────
        all_faces = [srf_a.ToBrep(), srf_b.ToBrep()]
        if cap_bot: all_faces += list(cap_bot)
        if cap_top: all_faces += list(cap_top)
        if end0:    all_faces += list(end0)
        if end1:    all_faces += list(end1)

        joined = rg.Brep.JoinBreps(all_faces, tol)

        if joined and len(joined) > 0:
            walls.Add(joined[0], GH_Path(i))
            print("구간 {} OK".format(i))
        else:
            print("구간 {}: JoinBreps 실패 (faces={})".format(i, len(all_faces)))

    print("완료: {}개 벽체".format(walls.DataCount))

    # ── 타입 확인 디버그 ─────────────────────────────────────
    for path in walls.Paths:
        for item in walls.Branch(path):
            print("wall type: {}  IsValid: {}".format(
                type(item).__name__,
                item.IsValid if item else "None"))
            break  # 첫 번째만 확인
        break
