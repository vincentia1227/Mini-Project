"""
Title : Slab

"""


import Rhino.Geometry as rg
import scriptcontext as sc

# Guid → Curve 객체로 변환
if isinstance(curve, rg.Curve):
    crv = curve
else:
    crv = sc.doc.Objects.Find(curve).Geometry

# Step 1. 닫힌 커브에 면 생성
tol = sc.doc.ModelAbsoluteTolerance
breps = rg.Brep.CreatePlanarBreps(crv, tol)

if not breps or len(breps) == 0:
    print("❌ 면 생성 실패!")
    a = None
else:
    print("✅ 면 생성 성공!")
    base_brep = breps[0]

    # Step 2. -Z방향으로 height 만큼 extrude
    extrude_vec = rg.Vector3d(0, 0, -height)
    extrude_srf = rg.Surface.CreateExtrusion(crv, extrude_vec)

    if extrude_srf:
        solid = extrude_srf.ToBrep()
        # 캡(상단/하단 면) 추가해서 솔리드로 만들기
        capped = solid.CapPlanarHoles(tol)
        if capped:
            print("✅ Extrude 솔리드 성공!")
            a = capped
        else:
            print("✅ Extrude 성공 (캡 없음)")
            a = solid
    else:
        print("❌ Extrude 실패!")
        a = base_brep