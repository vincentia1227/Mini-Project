# Mini project-2 — Grasshopper Python scripts

This folder contains **Grasshopper Python** components (GhPython) for **Rhino 3D** geometry: layout and massing helpers for corridor, slab, wall, nurse-station (NS) office, bed placement, and sliding doors. Scripts use **RhinoCommon** (`Rhino.Geometry`, `scriptcontext`).

**Location of scripts:** `2. Python Script/`

---

## Environment

- **Rhino** with **Grasshopper**
- Paste each file into a **Python** script component (or reference it), and wire inputs/outputs to match the variable names used in the script (`curve`, `solid`, `a`, `result`, etc., depending on the file).

---

## Script reference

### `#P2_Bed Layout.py` — Bed layout along a curve

- **Purpose**: Instances a **block definition** (or brep geometry) at regular **spacing** along a **guide curve**, oriented with the curve tangent (XY) and avoiding overlaps using bounding-box checks.
- **Typical inputs** (Grasshopper-side): `block` (brep / block instance / GUID), `curve` (curve or GUID), `spacing` (positive number). For **open** curves, optional `offset_into_curve` and `flip` nudge placement perpendicular to the curve.
- **Output**: List `a` of duplicated/transformed geometries added to the output tree.
- **Behavior**: Switches `scriptcontext` to the active Rhino document to resolve GUIDs. **Closed** curves use the full length; **open** curves inset by half the block’s long axis so ends stay inside. Prints an error if the curve is too short.

---

### `#P2_Sliding Door.py` — Voids and sliding door panels on a solid

- **Purpose**: Cuts **void boxes** at both ends of a **reference curve** on an extruded **solid**, then builds **two-panel sliding doors** per void (four door breps total for two voids).
- **Inputs**: `solid` (Brep), `curve`, `height`, `width` (full opening width; each leaf is half), `door_thickness`, `open_factor` (0 = closed, 1 = fully open, clamped).
- **Outputs**: `result` (solid after boolean difference), `doors` (list of door breps), `preview` (void boxes for checking).
- **Notes**: Void bottom Z comes from the solid bounding box. Inward direction at curve ends follows curve tangent in XY for boolean and panel placement.

---

### `#P2_NS Office.py` — Straight wall from centerline

- **Purpose**: Builds a **closed wall solid** (Brep) from a **plan curve** by offsetting **±thickness/2** in XY, lofting the offset pair for the base, extruding sides, capping ends, and joining.
- **Inputs**: `curve`, `thickness`, `height`.
- **Output**: `wall` (single Brep when join succeeds).
- **Notes**: Resolves `curve` from a list/tuple or Rhino object GUID via `scriptcontext`.

---

### `#P2_NS Office Divide.py` — Partition walls on a surface grid

- **Purpose**: Divides a **surface** (or first face of a Brep) into strips using **iso-curves**, then builds a **wall-height solid** per strip with the given **thickness** (offset iso-curve, extrude, cap, join).
- **Inputs**: `surface`, `divisions` (count ≥ 1), `wall_height`, `wall_thickness`, `use_v_dir` (False = divide along U / iso in V; True = divide along V / iso in U).
- **Outputs**: `walls` and `frames` as **DataTrees** (`Grasshopper.DataTree`), one branch per division index.
- **Notes**: Useful for subdividing an office footprint drawn on a surface.

---

### `#P2_Corridor.py` — Corridor strip and rail trimming

- **Purpose**: Offsets a **center curve** by **±offset_distance** in XY, **lofts** the two offsets into corridor surfaces, then optionally **splits a rail curve** at intersections with the offset curves and returns segments **outside** the corridor (by midpoint proximity to the loft brep).
- **Inputs**: `curve`, `offset_distance`, `rail` (optional; curve or GUID).
- **Outputs** (named in code): `b` = first offset curve, `c` = second offset curve, `d` = lofted surfaces, `e` = rail segments kept outside the corridor; `a` is unused (set to `None`).

---

### `#P2_Slab.py` — Planar slab extruded downward

- **Purpose**: Turns a **closed planar curve** into a **slab solid** by creating a planar Brep, then extruding along **−Z** by `height` and capping to form a solid.
- **Inputs**: `curve` (curve or GUID), `height` (extrusion depth, positive).
- **Output**: `a` (Brep solid or fallback planar brep if extrusion/cap fails).

---

### `#P2_NS(Nurse Station).py` — Partial nurse-station mass along a curve

- **Purpose**: On a subset of a **guide curve** (trimmed around a **center point** and **solid length**), offsets by `offset_distance`, picks **inner or outer** offset using `flip` and bounding-box size, then **lofts** base curve to offset and **extrudes** upward to `extrude_height` to produce wall-like solids.
- **Inputs**: `curve`, `offset_distance`, `extrude_height`, `flip` (True ≈ outer offset choice, False ≈ inner), `solid_length` (clamped to curve length), `center_point` (optional; closest point on curve defines trim center).
- **Outputs**: `a` = list with working curve + selected offset curve; `b` = loft surfaces; `c` = extruded breps (or joined solids from fallback path).

---

### `#P2_Wall.py` — Wall with top and base offsets

- **Purpose**: From a **plan curve** and **thickness**, offsets once in XY, then builds a closed solid between a **lower level** (−`depth` in Z) and **upper level** (+`height` in Z) using lofts between original and offset curves at bottom and top.
- **Inputs**: `curve`, `thickness`, `height` (up from reference), `depth` (down from reference).
- **Output**: `a` (joined Brep, or list of faces if join fails).

---

## Project notes (from `Readme.txt`)

- **Known issue**: In **non-rectangular** regions, partitioned **NS annex** walls from the scripts can extend **beyond the outer boundary curve**. This is acknowledged for future correction.
- **Setup hints**: Workflow uses a **centerline** and an **outer curve**. For **bed layout**, the **`flip`** boolean compensates for cases where beds end up on the wrong side of the curve depending on curve direction.

---

## File list

| File | Topic |
|------|--------|
| `#P2_Bed Layout.py` | Beds along curve |
| `#P2_Sliding Door.py` | Door voids + sliding panels |
| `#P2_NS Office.py` | Wall from centerline |
| `#P2_NS Office Divide.py` | Walls from surface divisions |
| `#P2_Corridor.py` | Corridor loft + rail split |
| `#P2_Slab.py` | Downward-extruded slab |
| `#P2_NS(Nurse Station).py` | Trimmed NS mass |
| `#P2_Wall.py` | Wall with height and depth |
