"""
Title : Wall

"""


import Rhino.Geometry as rg
import scriptcontext as sc

# GUID를 Curve 객체로 변환
def get_curve(input_curve):
    if isinstance(input_curve, rg.Curve):
        return input_curve
    else:
        rhino_obj = sc.doc.Objects.Find(input_curve)
        if rhino_obj:
            return rhino_obj.Geometry
    return None

# 메인 코드
if curve and thickness and height and depth:
    
    crv = get_curve(curve)
    
    if crv:
        # 1. 커브를 thickness 만큼 offset
        offset_curves = crv.Offset(
            rg.Plane.WorldXY, 
            thickness, 
            sc.doc.ModelAbsoluteTolerance, 
            rg.CurveOffsetCornerStyle.Sharp
        )
        
        if offset_curves and len(offset_curves) > 0:
            offset_crv = offset_curves[0]
            
            # 2. 위로 복사 (height)
            vector_up = rg.Vector3d(0, 0, height)
            transform_up = rg.Transform.Translation(vector_up)
            
            crv_top = crv.DuplicateCurve()
            crv_top.Transform(transform_up)
            
            offset_crv_top = offset_crv.DuplicateCurve()
            offset_crv_top.Transform(transform_up)

            # 3. 아래로 복사 (-depth)
            vector_down = rg.Vector3d(0, 0, -depth)
            transform_down = rg.Transform.Translation(vector_down)

            crv_bottom = crv.DuplicateCurve()
            crv_bottom.Transform(transform_down)

            offset_crv_bottom = offset_crv.DuplicateCurve()
            offset_crv_bottom.Transform(transform_down)
            
            # 4. 면들 생성
            # 상단 면 (height 위치)
            top = rg.Brep.CreateFromLoft(
                [crv_top, offset_crv_top], 
                rg.Point3d.Unset, rg.Point3d.Unset, 
                rg.LoftType.Straight, False
            )[0]

            # 하단 면 (-depth 위치)
            bottom = rg.Brep.CreateFromLoft(
                [crv_bottom, offset_crv_bottom], 
                rg.Point3d.Unset, rg.Point3d.Unset, 
                rg.LoftType.Straight, False
            )[0]
            
            # 외벽 (crv_bottom → crv_top)
            outer_wall = rg.Brep.CreateFromLoft(
                [crv_bottom, crv_top], 
                rg.Point3d.Unset, rg.Point3d.Unset, 
                rg.LoftType.Straight, False
            )[0]
            
            # 내벽 (offset_crv_bottom → offset_crv_top)
            inner_wall = rg.Brep.CreateFromLoft(
                [offset_crv_bottom, offset_crv_top], 
                rg.Point3d.Unset, rg.Point3d.Unset, 
                rg.LoftType.Straight, False
            )[0]
            
            # 모든 면 결합
            all_surfaces = [bottom, top, outer_wall, inner_wall]
            joined = rg.Brep.JoinBreps(all_surfaces, sc.doc.ModelAbsoluteTolerance)
            
            if joined and len(joined) > 0:
                a = joined[0]
            else:
                a = all_surfaces
        else:
            a = None
    else:
        a = None
else:
    a = None