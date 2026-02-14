from pyrevit import revit, DB, forms, script

doc = revit.doc
uidoc = revit.uidoc
logger = script.get_logger()

# -------------------------------
# 1. Get selected grids
# -------------------------------
selection_ids = uidoc.Selection.GetElementIds()

if not selection_ids:
    forms.alert("Please select grids first.", exitscript=True)

# Filter only grid elements
grids = []
for eid in selection_ids:
    el = doc.GetElement(eid)
    if isinstance(el, DB.Grid):
        grids.append(el)

if len(grids) < 2:
    forms.alert("Please select at least 2 grids.", exitscript=True)

logger.info("Number of selected grids: {}".format(len(grids)))

# -------------------------------
# 2. Get column family types
# -------------------------------
collector = DB.FilteredElementCollector(doc)\
    .OfClass(DB.FamilySymbol)\
    .OfCategory(DB.BuiltInCategory.OST_StructuralColumns)

column_types = {}
for symbol in collector:
    if symbol.Family:
        family_name = symbol.Family.Name
        type_name = symbol.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
        display_name = "{} : {}".format(family_name, type_name)
        column_types[display_name] = symbol

if not column_types:
    forms.alert("No structural column families found in project.", exitscript=True)

# Let user select column type
selected_type_name = forms.SelectFromList.show(
    sorted(column_types.keys()),
    title="Select Column Type",
    button_name="Select",
    multiselect=False
)

if not selected_type_name:
    script.exit()

column_symbol = column_types[selected_type_name]

# -------------------------------
# 3. Get levels
# -------------------------------
levels_collector = DB.FilteredElementCollector(doc)\
    .OfClass(DB.Level)\
    .WhereElementIsNotElementType()

levels = list(levels_collector)
if not levels:
    forms.alert("No levels found in project.", exitscript=True)

# Sort levels by elevation
levels.sort(key=lambda x: x.Elevation)

level_dict = {level.Name: level for level in levels}

# Let user select base level
selected_level_name = forms.SelectFromList.show(
    [level.Name for level in levels],
    title="Select Base Level for Columns",
    button_name="Select",
    multiselect=False
)

if not selected_level_name:
    script.exit()

base_level = level_dict[selected_level_name]

# Let user select top level
top_level_name = forms.SelectFromList.show(
    [level.Name for level in levels if level.Elevation > base_level.Elevation],
    title="Select Top Level for Columns",
    button_name="Select",
    multiselect=False
)

if not top_level_name:
    script.exit()

top_level = level_dict[top_level_name]

# -------------------------------
# 4. Find grid intersections
# -------------------------------
def get_grid_curve(grid):
    """Get the curve of a grid"""
    return grid.Curve

def find_intersection_point(curve1, curve2):
    """Find intersection point between two curves"""
    try:
        # Use IntersectWithCurveArray method
        intersection_result = curve1.Intersect(curve2)
        
        if intersection_result == DB.SetComparisonResult.Overlap:
            # Get intersection details
            result_array = clr.Reference[DB.IntersectionResultArray]()
            intersection_status = curve1.Intersect(curve2, result_array)
            
            if result_array.Value and result_array.Value.Size > 0:
                return result_array.Value.get_Item(0).XYZPoint
        
    except:
        # Alternative method using clr reference
        try:
            import clr
            result = clr.Reference[DB.IntersectionResultArray]()
            comparison = curve1.Intersect(curve2, result)
            
            if comparison == DB.SetComparisonResult.Overlap:
                if result.Value and result.Value.Size > 0:
                    return result.Value.get_Item(0).XYZPoint
        except:
            pass
    
    return None

intersection_points = []

# Check all grid pairs for intersections
for i in range(len(grids)):
    for j in range(i + 1, len(grids)):
        curve1 = get_grid_curve(grids[i])
        curve2 = get_grid_curve(grids[j])
        
        point = find_intersection_point(curve1, curve2)
        if point:
            # Check for duplicate points (tolerance: 0.001 ft)
            is_duplicate = False
            for existing_point in intersection_points:
                if existing_point.DistanceTo(point) < 0.001:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                intersection_points.append(point)

if not intersection_points:
    forms.alert("No grid intersections found.", exitscript=True)

logger.info("Number of intersections found: {}".format(len(intersection_points)))

# -------------------------------
# 5. Place columns at intersections
# -------------------------------
with revit.Transaction("Place Columns at Grid Intersections"):
    # Activate the column symbol if not active
    if not column_symbol.IsActive:
        column_symbol.Activate()
        doc.Regenerate()
    
    placed_count = 0
    failed_count = 0
    
    for point in intersection_points:
        try:
            # Create a new instance of structural column
            new_column = doc.Create.NewFamilyInstance(
                point,
                column_symbol,
                base_level,
                DB.Structure.StructuralType.Column
            )
            
            # Set top level
            top_level_param = new_column.get_Parameter(
                DB.BuiltInParameter.FAMILY_TOP_LEVEL_PARAM
            )
            if top_level_param and not top_level_param.IsReadOnly:
                top_level_param.Set(top_level.Id)
            
            # Set base offset to 0
            base_offset_param = new_column.get_Parameter(
                DB.BuiltInParameter.FAMILY_BASE_LEVEL_OFFSET_PARAM
            )
            if base_offset_param and not base_offset_param.IsReadOnly:
                base_offset_param.Set(0.0)
            
            # Set top offset to 0
            top_offset_param = new_column.get_Parameter(
                DB.BuiltInParameter.FAMILY_TOP_LEVEL_OFFSET_PARAM
            )
            if top_offset_param and not top_offset_param.IsReadOnly:
                top_offset_param.Set(0.0)
            
            placed_count += 1
            
        except Exception as e:
            logger.error("Failed to place column: {}".format(e))
            failed_count += 1

# -------------------------------
# 6. Report results
# -------------------------------
message = "Column placement completed!\n\n"
message += "Columns placed: {}\n".format(placed_count)
if failed_count > 0:
    message += "Failed: {}".format(failed_count)

forms.alert(message, title="BIM Pure")