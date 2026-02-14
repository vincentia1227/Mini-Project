from pyrevit import revit, DB, forms, script
import re

doc = revit.doc
uidoc = revit.uidoc
logger = script.get_logger()

# -------------------------------
# 1. Get all sheets or selected sheets
# -------------------------------
selection_ids = uidoc.Selection.GetElementIds()

sheets = []

if selection_ids:
    # Use selected elements
    for eid in selection_ids:
        el = doc.GetElement(eid)
        if isinstance(el, DB.ViewSheet):
            sheets.append(el)
else:
    # Get all sheets in project
    collector = DB.FilteredElementCollector(doc)\
        .OfClass(DB.ViewSheet)\
        .WhereElementIsNotElementType()
    
    sheets = list(collector)

if not sheets:
    forms.alert("No sheets found. Please select sheets or ensure project has sheets.", exitscript=True)

logger.info("Number of sheets: {}".format(len(sheets)))

# -------------------------------
# 2. Sort sheets by current sheet number
# -------------------------------
sheets.sort(key=lambda x: x.SheetNumber)

# Show current sheet list
current_sheets = ["{} - {}".format(s.SheetNumber, s.Name) for s in sheets]
logger.info("Current sheets:\n{}".format("\n".join(current_sheets)))

# -------------------------------
# 3. Get starting sheet number from user
# -------------------------------
starting_number = forms.ask_for_string(
    prompt="Enter the starting sheet number (e.g., A1-101):",
    title="Starting Sheet Number"
)

if not starting_number:
    script.exit()

# -------------------------------
# 4. Parse the sheet number pattern
# -------------------------------
def parse_sheet_number(sheet_num):
    """
    Parse sheet number to extract prefix and number
    Examples: 
    - A1-101 -> prefix='A1-', number=101
    - A-001 -> prefix='A-', number=1
    - 101 -> prefix='', number=101
    """
    # Find the last sequence of digits
    match = re.search(r'^(.*?)(\d+)$', sheet_num)
    
    if match:
        prefix = match.group(1)
        number = int(match.group(2))
        num_digits = len(match.group(2))
        return prefix, number, num_digits
    else:
        forms.alert("Invalid sheet number format. Please include a number at the end.", exitscript=True)

prefix, start_num, num_digits = parse_sheet_number(starting_number)

logger.info("Prefix: '{}', Starting number: {}, Digits: {}".format(prefix, start_num, num_digits))

# -------------------------------
# 5. Preview new sheet numbers
# -------------------------------
new_sheet_numbers = []
for i, sheet in enumerate(sheets):
    new_number = start_num + i
    # Format with leading zeros
    new_sheet_num = "{}{}".format(prefix, str(new_number).zfill(num_digits))
    new_sheet_numbers.append(new_sheet_num)

# Show preview
preview_text = "Preview of new sheet numbers:\n\n"
for i, sheet in enumerate(sheets):
    preview_text += "{} -> {}\n".format(sheet.SheetNumber, new_sheet_numbers[i])

logger.info(preview_text)

# Ask for confirmation
confirm = forms.alert(
    preview_text + "\nDo you want to proceed?",
    title="Confirm Sheet Renaming",
    yes=True,
    no=True
)

if not confirm:
    script.exit()

# -------------------------------
# 6. Rename sheets
# -------------------------------
with revit.Transaction("Rename Sheets Sequentially"):
    success_count = 0
    failed_count = 0
    
    # First pass: Rename to temporary numbers to avoid conflicts
    temp_numbers = []
    for i, sheet in enumerate(sheets):
        temp_num = "TEMP_{}".format(i)
        temp_numbers.append(temp_num)
        try:
            sheet.SheetNumber = temp_num
        except Exception as e:
            logger.error("Failed to set temp number for sheet {}: {}".format(sheet.SheetNumber, e))
    
    doc.Regenerate()
    
    # Second pass: Set final numbers
    for i, sheet in enumerate(sheets):
        try:
            sheet.SheetNumber = new_sheet_numbers[i]
            logger.info("Renamed: {} -> {}".format(temp_numbers[i], new_sheet_numbers[i]))
            success_count += 1
        except Exception as e:
            logger.error("Failed to rename sheet: {}".format(e))
            failed_count += 1

# -------------------------------
# 7. Report results
# -------------------------------
message = "Sheet renaming completed!\n\n"
message += "Successfully renamed: {}\n".format(success_count)
if failed_count > 0:
    message += "Failed: {}".format(failed_count)

forms.alert(message, title="BIM Pure")