"""
-------------------------------------------------
Tool Name: Set Parameter Value
Description:
    Set a parameter value to all selected elements.
Author: BIM Pure
-------------------------------------------------
"""
# -*- coding: utf-8 -*-
"""
-------------------------------------------------
Tool Name: Set Parameter Value
Description:
    Set a parameter value to all selected elements.
    (Length parameters are assumed to be entered in mm)
Author: BIM Pure
-------------------------------------------------
"""

from pyrevit import revit, DB, forms, script

doc = revit.doc
uidoc = revit.uidoc
logger = script.get_logger()

# -------------------------------
# 1. Get selected elements
# -------------------------------
selection_ids = uidoc.Selection.GetElementIds()

if not selection_ids:
    forms.alert("At First, You need to Select elements.", exitscript=True)

elements = [doc.GetElement(eid) for eid in selection_ids]

# -------------------------------
# 2. Ask user for parameter name
# -------------------------------
param_name = forms.ask_for_string(
    prompt="Enter the name of Parameter Accurately",
    title="Parameter Name"
)

if not param_name:
    script.exit()

# -------------------------------
# 3. Ask user for value (mm)
# -------------------------------
param_value = forms.ask_for_string(
    prompt="Enter the value.(mm)",
    title="Parameter Value"
)

if param_value is None:
    script.exit()

# -------------------------------
# 4. Start transaction
# -------------------------------
with revit.Transaction("Set Parameter Value"):
    for el in elements:
        param = el.LookupParameter(param_name)

        if not param:
            logger.warning(
                "Element {} has no parameter '{}'".format(el.Id, param_name)
            )
            continue

        if param.IsReadOnly:
            logger.warning(
                "Parameter '{}' is read-only on element {}".format(
                    param_name, el.Id
                )
            )
            continue

        # -------------------------------
        # 5. Set value based on StorageType
        # -------------------------------
        st = param.StorageType

        try:
            if st == DB.StorageType.String:
                param.Set(param_value)

            elif st == DB.StorageType.Integer:
                param.Set(int(param_value))

            elif st == DB.StorageType.Double:
                value_internal = DB.UnitUtils.ConvertToInternalUnits(
                    float(param_value),
                    DB.UnitTypeId.Millimeters
                )
                param.Set(value_internal)

            else:
                logger.warning(
                    "Unsupported StorageType on element {}".format(el.Id)
                )

        except Exception as e:
            logger.error(
                "Failed to set parameter on element {}: {}".format(el.Id, e)
            )

# -------------------------------
# 6. Done
# -------------------------------
forms.alert("Complete entering the parameter!", title="BIM Pure")

