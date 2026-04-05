"""
Title : Sliding Door
Grasshopper Python Script Component
=====================================
Inputs:
    solid          : Brep  - Extruded Solid
    curve          : Curve - 기준 커브
    height         : float - Void/도어 높이 (아래에서 위로)
    width          : float - Void/도어 전체 너비 (도어 한 짝 = width/2)
    door_thickness : float - 도어 두께
    open_factor    : float - 슬라이딩 열림 비율 (0.0=닫힘 ~ 1.0=열림) → Slider

Outputs:
    result  : Brep       - Void가 생성된 Solid
    doors   : List[Brep] - 슬라이딩 도어 (각 Void마다 2짝, 총 4개)
    preview : List[Brep] - Void Box (확인용)


"""

import Rhino.Geometry as rg


def unwrap(val):
    if isinstance(val, (list, tuple)):
        return val[0] if len(val) > 0 else None
    return val


def get_solid_bbox(brep):
    return brep.GetBoundingBox(True)


def get_tangent_inward(curve, at_start):
    """
    Curve 끝점의 접선 (XY 투영, 단위화).
    Solid 안쪽(Void 깊이 방향)을 향하도록:
      시작점 → Curve 진행 방향
      끝점   → Curve 진행 방향의 반대
    """
    t = curve.Domain.Min if at_start else curve.Domain.Max
    tan = curve.TangentAt(t)
    tan.Z = 0
    tan.Unitize()
    if not at_start:
        tan = rg.Vector3d(-tan.X, -tan.Y, 0)
    return tan


def create_void_box(center_pt, bottom_z, width, height):
    """
    center_pt XY, bottom_z 에서 Z 위로 height 의 Void Box (width x width).
    """
    half = width / 2.0
    plane = rg.Plane(
        rg.Point3d(center_pt.X, center_pt.Y, bottom_z),
        rg.Vector3d.ZAxis
    )
    box = rg.Box(plane,
                 rg.Interval(-half, half),
                 rg.Interval(-half, half),
                 rg.Interval(0, height))
    return box.ToBrep()


def create_door_panel(void_center, bottom_z,
                      inward_vec, perp_vec,
                      half_width, height, thickness,
                      side_sign, open_factor):
    """
    슬라이딩 도어 한 짝.

    닫힘 위치:
        - Z: bottom_z ~ bottom_z + height  (Void와 동일한 Z 범위)
        - perp_vec 방향: side_sign * half_width/2  (두 짝이 중앙에서 맞닿음)
        - inward_vec 방향: thickness/2  (도어 앞면이 Solid 외부 표면에 붙음)

    슬라이딩:
        - perp_vec 방향으로 side_sign * open_factor * half_width 이동  ★
    """
    # 닫힘: perp 방향 center
    perp_offset  = side_sign * (half_width / 2.0)
    # 닫힘: inward 방향 (두께의 절반만큼 Void 안으로)
    tang_offset  = thickness / 2.0

    closed_x = void_center.X + perp_vec.X * perp_offset + inward_vec.X * tang_offset
    closed_y = void_center.Y + perp_vec.Y * perp_offset + inward_vec.Y * tang_offset

    # 슬라이딩: perp_vec 방향 ★
    slide_dist = side_sign * open_factor * half_width
    final_x = closed_x + perp_vec.X * slide_dist
    final_y = closed_y + perp_vec.Y * slide_dist

    hw = half_width / 2.0
    ht = thickness  / 2.0

    # 8개 꼭짓점: perp_vec(X) inward_vec(Y) World-Z(Z) 기준
    def pt(px, py, pz):
        return rg.Point3d(
            final_x + perp_vec.X * px + inward_vec.X * py,
            final_y + perp_vec.Y * px + inward_vec.Y * py,
            bottom_z + pz
        )

    b0 = pt(-hw, -ht, 0);      b1 = pt(hw, -ht, 0)
    b2 = pt( hw,  ht, 0);      b3 = pt(-hw, ht, 0)
    t0 = pt(-hw, -ht, height); t1 = pt(hw, -ht, height)
    t2 = pt( hw,  ht, height); t3 = pt(-hw, ht, height)

    faces = [
        rg.Brep.CreateFromCornerPoints(b0, b1, b2, b3, 0.001),
        rg.Brep.CreateFromCornerPoints(t0, t3, t2, t1, 0.001),
        rg.Brep.CreateFromCornerPoints(b0, b1, t1, t0, 0.001),
        rg.Brep.CreateFromCornerPoints(b3, b2, t2, t3, 0.001),
        rg.Brep.CreateFromCornerPoints(b0, b3, t3, t0, 0.001),
        rg.Brep.CreateFromCornerPoints(b1, b2, t2, t1, 0.001),
    ]
    faces = [f for f in faces if f is not None]
    if not faces:
        print("Warning: face 생성 실패")
        return None

    joined = rg.Brep.JoinBreps(faces, 0.01)
    if joined and len(joined) > 0:
        return joined[0]
    print("Warning: JoinBreps 실패")
    return None


def create_sliding_doors(void_center, bottom_z, width, height,
                         thickness, inward_vec, open_factor):
    """Void 하나에 슬라이딩 도어 2짝."""
    half_width = width / 2.0

    # perp = inward_vec 의 XY 수직 = 슬라이딩 방향 ★
    perp_vec = rg.Vector3d(-inward_vec.Y, inward_vec.X, 0)
    perp_vec.Unitize()

    door_r = create_door_panel(void_center, bottom_z,
                               inward_vec, perp_vec,
                               half_width, height, thickness,
                               +1, open_factor)
    door_l = create_door_panel(void_center, bottom_z,
                               inward_vec, perp_vec,
                               half_width, height, thickness,
                               -1, open_factor)
    return [d for d in [door_r, door_l] if d is not None and d.IsValid]


def run():
    # ── Input 정규화 ─────────────────────────────────────────────
    _solid     = unwrap(solid)
    _curve     = unwrap(curve)
    _height    = unwrap(height)
    _width     = unwrap(width)
    _thickness = unwrap(door_thickness)
    _open      = unwrap(open_factor)

    if _open is None: _open = 0.0
    _open = max(0.0, min(1.0, float(_open)))

    # ── 유효성 검사 ──────────────────────────────────────────────
    errors = []
    if _solid     is None:                    errors.append("solid")
    if _curve     is None:                    errors.append("curve")
    if _height    is None or _height    <= 0: errors.append("height")
    if _width     is None or _width     <= 0: errors.append("width")
    if _thickness is None or _thickness <= 0: errors.append("door_thickness")

    if errors:
        print("Error: " + ", ".join(errors))
        return None, [], []

    # ── Solid BBox → bottom_z ────────────────────────────────────
    bbox     = get_solid_bbox(_solid)
    bottom_z = bbox.Min.Z
    print("bottom_z={:.3f}  open={:.2f}".format(bottom_z, _open))

    # ── Curve 끝점 & Inward 접선 ─────────────────────────────────
    start_pt     = _curve.PointAtStart
    end_pt       = _curve.PointAtEnd
    inward_start = get_tangent_inward(_curve, at_start=True)
    inward_end   = get_tangent_inward(_curve, at_start=False)
    print("inward_start={}  inward_end={}".format(inward_start, inward_end))

    # ── Void Box 생성 ────────────────────────────────────────────
    void_s = create_void_box(start_pt, bottom_z, _width, _height)
    void_e = create_void_box(end_pt,   bottom_z, _width, _height)
    void_boxes = [void_s, void_e]

    # ── Boolean Difference ───────────────────────────────────────
    result_brep = _solid
    for i, vbox in enumerate(void_boxes):
        label = ["시작점", "끝점"][i]
        if vbox is None or not vbox.IsValid:
            print("Warning: {} Void 유효하지 않음".format(label))
            continue
        diff = rg.Brep.CreateBooleanDifference([result_brep], [vbox], 0.01)
        if diff and len(diff) > 0:
            result_brep = diff[0]
            print("{} Void 완료".format(label))
        else:
            print("Warning: {} Boolean Difference 실패".format(label))

    # ── 슬라이딩 도어 생성 ───────────────────────────────────────
    all_doors  = []
    all_doors += create_sliding_doors(
        start_pt, bottom_z, _width, _height, _thickness, inward_start, _open)
    all_doors += create_sliding_doors(
        end_pt,   bottom_z, _width, _height, _thickness, inward_end,   _open)

    print("도어 생성 완료: 총 {}개".format(len(all_doors)))
    return result_brep, all_doors, void_boxes


# ── 실행 ────────────────────────────────────────────────────────
result, doors, preview = run()
