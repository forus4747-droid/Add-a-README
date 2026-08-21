# -*- coding: utf-8 -*-
"""Add a `Sprint` tab to PaydayCockpit25. Touches nothing else except sheet order."""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule
from openpyxl.comments import Comment
from openpyxl.utils import get_column_letter

SRC = '/home/user/work/PaydayCockpit25_Aug21-filled_1.xlsx'
OUT = '/home/user/work/PaydayCockpit26_Sprint.xlsx'

NAVY   = '1F3864'   # header rows / title text
BLUE   = '2E5496'   # section bars
YELLOW = 'FFFF00'   # Jay types here
LTRED  = 'FFC7CE'   # kill row
GREY   = '808080'
GREEN  = '006100'
RED    = '9C0006'
AMBER  = '9C6500'
BAND   = 'F2F2F2'

F_TITLE = Font(name='Arial', size=16, bold=True, color=NAVY)
F_SUB   = Font(name='Arial', size=9,  italic=True, color=GREY)
F_BAR   = Font(name='Arial', size=11, bold=True, color='FFFFFF')
F_HDR   = Font(name='Arial', size=8,  bold=True, color='FFFFFF')
F_LBL   = Font(name='Arial', size=9,  bold=True, color='000000')
F_DAT   = Font(name='Arial', size=9,  color='000000')
F_NOTE  = Font(name='Arial', size=8,  italic=True, color=GREY)
F_KILL  = Font(name='Arial', size=11, bold=True, color=RED)
F_BIG   = Font(name='Arial', size=14, bold=True, color=NAVY)

FILL_BAR  = PatternFill('solid', fgColor=BLUE)
FILL_HDR  = PatternFill('solid', fgColor=NAVY)
FILL_IN   = PatternFill('solid', fgColor=YELLOW)
FILL_KILL = PatternFill('solid', fgColor=LTRED)
FILL_BAND = PatternFill('solid', fgColor=BAND)

THIN = Side(style='thin', color='BFBFBF')
BOX  = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

WRAP = Alignment(horizontal='left', vertical='top', wrap_text=True)
CTR  = Alignment(horizontal='center', vertical='center', wrap_text=True)
LFT  = Alignment(horizontal='left', vertical='center', wrap_text=True)

# ---------------------------------------------------------------- row plan
R_TITLE, R_SUB, R_LEGEND = 1, 2, 3
A_BAR, A_HDR, A_VAL = 4, 5, 6
B_BAR = 8
B_NO, B_START, B_END, B_DEMO, B_SHOW, B_WHY = 9, 10, 11, 12, 13, 14
B_DONE1, B_DONE2, B_DONE3, B_STATUS, B_LEFT = 15, 16, 17, 18, 19
K_BAR, K_WHAT, K_HRS = 20, 21, 22
C_BAR, C_HDR, C_D1, C_NOTE = 24, 25, 26, 29
D_BAR, D_HDR, D_KEY, D_TGT, D_B1, D_B2, D_B3, D_RULE, D_CAS = 31, 32, 33, 34, 35, 36, 37, 38, 39
E_BAR, E_HDR, E_FIRST, E_LAST, E_NOTE = 41, 42, 43, 52, 53
F_BAR, F_HDR, F_FIRST, F_LAST, F_NOTE = 55, 56, 57, 69, 70
G_BAR, G_HDR, G_FIRST, G_LAST = 72, 73, 74, 78
H_BAR, H_FIRST = 80, 81

wb = openpyxl.load_workbook(SRC)
assert 'Sprint' not in wb.sheetnames
ws = wb.create_sheet('Sprint')
ws.sheet_properties.tabColor = 'FF0000'
ws.sheet_view.showGridLines = False
ws.freeze_panes = 'A4'

# ---------------------------------------------------------------- helpers
def put(coord, value, font=F_DAT, fill=None, align=None, fmt=None, border=False):
    c = ws[coord]
    c.value = value
    c.font = font
    if fill is not None:
        c.fill = fill
    if align is not None:
        c.alignment = align
    if fmt:
        c.number_format = fmt
    if border:
        c.border = BOX
    return c

def bar(row, text, first='B', last='I'):
    ws.merge_cells(f'{first}{row}:{last}{row}')
    put(f'{first}{row}', text, F_BAR, FILL_BAR, LFT)
    for col in range(ord(first) - 64, ord(last) - 64 + 1):
        ws.cell(row=row, column=col).fill = FILL_BAR
    ws.row_dimensions[row].height = 20

def header(row, cells):
    """cells: list of (span_or_col, text)"""
    for span, text in cells:
        if ':' in span:
            ws.merge_cells(f'{span.split(":")[0]}{row}:{span.split(":")[1]}{row}')
            first = span.split(':')[0]
            last = span.split(':')[1]
        else:
            first = last = span
        put(f'{first}{row}', text, F_HDR, FILL_HDR, CTR, border=True)
        for col in range(ord(first) - 64, ord(last) - 64 + 1):
            cc = ws.cell(row=row, column=col)
            cc.fill = FILL_HDR
            cc.border = BOX
    ws.row_dimensions[row].height = 26

def span(row, first, last, value=None, font=F_DAT, fill=None, align=WRAP, fmt=None, border=True):
    ws.merge_cells(f'{first}{row}:{last}{row}')
    put(f'{first}{row}', value, font, fill, align, fmt, border)
    for col in range(ord(first) - 64, ord(last) - 64 + 1):
        cc = ws.cell(row=row, column=col)
        if fill is not None:
            cc.fill = fill
        if border:
            cc.border = BOX
    return ws[f'{first}{row}']

# ---------------------------------------------------------------- widths
ws.column_dimensions['A'].width = 2
for col, w in zip('BCDEFGHI', [26, 18, 24, 18, 32, 20, 13, 11]):
    ws.column_dimensions[col].width = w

# ---------------------------------------------------------------- title
put('B1', 'SPRINT  ·  3 days. One demo. No switching.', F_TITLE)
ws.row_dimensions[1].height = 24
put('B2', 'One 3-day sprint at a time, each ending in a showable material difference. New ideas go to the Parking Lot, not into the sprint.', F_SUB)
span(R_LEGEND, 'B', 'I',
     'YELLOW cells = you type.  Everything else computes.   ·   LIGHT-RED = the kill row: filling it in writing is the only legal way to quit a sprint.',
     F_NOTE, None, LFT, border=False)

# ---------------------------------------------------------------- BLOCK A
bar(A_BAR, 'SCOREBOARD  ·  the only numbers that matter')
header(A_HDR, [('B', 'Sprints started'), ('C', 'Sprints SHIPPED'), ('D', 'Ship rate'),
               ('E', 'Current chain'), ('F', 'Deep-work hrs (all-time)'),
               ('G:I', 'Ideas parked (resisted pivots)')])
LOG = f'$B${F_FIRST}:$B${F_LAST}'
put(f'B{A_VAL}', f'=COUNTA({LOG})', F_BIG, None, CTR, '0', True)
put(f'C{A_VAL}', f'=COUNTIF($F${F_FIRST}:$F${F_LAST},"SHIPPED ✓")', F_BIG, None, CTR, '0', True)
put(f'D{A_VAL}', f'=IFERROR(C{A_VAL}/B{A_VAL},0)', F_BIG, None, CTR, '0%', True)
put(f'E{A_VAL}', f'=IFERROR(LOOKUP(2,1/($I${F_FIRST}:$I${F_LAST}<>""),$I${F_FIRST}:$I${F_LAST}),0)',
    F_BIG, None, CTR, '0', True)
put(f'F{A_VAL}', f'=SUM($H${F_FIRST}:$H${F_LAST})', F_BIG, None, CTR, '0.0', True)
span(A_VAL, 'G', 'I', f'=COUNTA($C${E_FIRST}:$C${E_LAST})', F_BIG, None, CTR, '0')
ws.row_dimensions[A_VAL].height = 26

# ---------------------------------------------------------------- BLOCK B
bar(B_BAR, 'CURRENT SPRINT  ·  contract — filled BEFORE day 1, frozen after')

def label(row, text):
    put(f'B{row}', text, F_LBL, None, LFT, border=True)

label(B_NO, 'Sprint #')
put(f'C{B_NO}', None, F_DAT, FILL_IN, CTR, '0', True)
label(B_START, 'Start date')
put(f'C{B_START}', None, F_DAT, FILL_IN, CTR, 'mmm dd yyyy', True)
label(B_END, 'End date   (= start + 2)')
put(f'C{B_END}', f'=IF($C${B_START}="","",$C${B_START}+2)', F_DAT, None, CTR, 'mmm dd yyyy', True)
label(B_DEMO, 'THE DEMO')
span(B_DEMO, 'C', 'I', None, F_DAT, FILL_IN)
ws[f'C{B_DEMO}'].comment = Comment(
    'One line. The showable artifact that EXISTS on day 3.\n'
    'Good: "a ranked table of 15 candidate categories".\n'
    'Not: "research categories".', 'Sprint tab')
label(B_SHOW, 'Showable to (a named human)')
span(B_SHOW, 'C', 'E', None, F_DAT, FILL_IN)
span(B_SHOW, 'F', 'I', 'Who sees it on day 3. Unsent = unshipped.', F_NOTE, None, LFT, border=False)
label(B_WHY, 'Why it moves the 90-day goal')
span(B_WHY, 'C', 'I', None, F_DAT, FILL_IN)
for i, row in enumerate([B_DONE1, B_DONE2, B_DONE3], start=1):
    label(row, f'Definition of DONE  ·  {i}')
    span(row, 'C', 'H', None, F_DAT, FILL_IN)
    put(f'I{row}', None, F_DAT, FILL_IN, CTR, border=True)
label(B_STATUS, 'Status')
put(f'C{B_STATUS}', None, Font(name='Arial', size=9, bold=True), FILL_IN, CTR, border=True)
label(B_LEFT, 'Days left')
put(f'C{B_LEFT}',
    f'=IF($C${B_END}="","",IF($C${B_END}-TODAY()>0,$C${B_END}-TODAY()&" days left",'
    f'IF($C${B_END}-TODAY()=0,"SHIP DAY","OVERDUE by "&TODAY()-$C${B_END}&" days")))',
    Font(name='Arial', size=9, bold=True), None, CTR, border=True)
span(B_LEFT, 'D', 'I', 'Day 3 ends with the demo SENT. Not drafted — sent.', F_NOTE, None, LFT, border=False)

# ---- kill row
span(K_BAR, 'B', 'I',
     'KILL ROW  ·  required before Status can be set to KILLED ✗ — both cells, in writing',
     F_KILL, FILL_KILL, LFT)
put(f'B{K_WHAT}', 'What killed it (evidence, not mood):', F_LBL, FILL_KILL, LFT, border=True)
span(K_WHAT, 'C', 'I', None, F_DAT, FILL_IN)
put(f'B{K_HRS}', 'Hours it cost:', F_LBL, FILL_KILL, LFT, border=True)
put(f'C{K_HRS}', None, F_DAT, FILL_IN, CTR, '0.0', True)
span(K_HRS, 'D', 'I', None, F_DAT, FILL_KILL, LFT)
ws[f'B{K_BAR}'].comment = Comment(
    "If you can't fill these honestly, you're not killing it — you're fleeing it. Back to work.",
    'Sprint tab')

# ---------------------------------------------------------------- BLOCK C
bar(C_BAR, 'THE 3 DAYS  ·  one micro-milestone each')
header(C_HDR, [('B', 'Day'), ('C', 'Date'), ('D', 'Day type ▾'), ('E', 'Business hrs target'),
               ('F', 'Micro-milestone'), ('G:H', 'Done ▾'), ('I', 'Actual hrs')])
for i in range(3):
    r = C_D1 + i
    put(f'B{r}', f'Day {i+1}', F_LBL, None, LFT, border=True)
    put(f'C{r}', f'=IF($C${B_START}="","",$C${B_START}+{i})', F_DAT, None, CTR, 'mmm dd yyyy', True)
    put(f'D{r}', None, F_DAT, FILL_IN, CTR, border=True)
    put(f'E{r}', f'=IFERROR(INDEX($C${D_TGT}:$H${D_TGT},MATCH($D{r},$C${D_KEY}:$H${D_KEY},0)),"")',
        F_DAT, None, CTR, '0.0', True)
    put(f'F{r}', None, F_DAT, FILL_IN, WRAP, border=True)
    span(r, 'G', 'H', None, F_DAT, FILL_IN, CTR)
    put(f'I{r}', None, F_DAT, FILL_IN, CTR, '0.0', True)
    ws.row_dimensions[r].height = 30
span(C_NOTE, 'B', 'I',
     'Size the micro-milestone to the day type. An Off day moves the sprint. A Day-shift day keeps it alive. '
     'Day 3 ends with the demo SENT.', F_NOTE, None, LFT, border=False)

# ---------------------------------------------------------------- BLOCK D
bar(D_BAR, 'DAY PLANNER  ·  your whole business day, by shift type')
header(D_HDR, [('B', ''), ('C:D', 'OFF DAY  ·  target 6.5h'),
               ('E:F', 'DAY SHIFT 6a–6p  ·  target 1.5h'),
               ('G:I', 'NIGHT SHIFT 6p–6a  ·  target 2.5h')])

planner = [
    (D_KEY,  'Day-type key  (matches the ▾)', 'Off', 'Day shift', 'Night shift'),
    (D_TGT,  'Business hrs target', 6.5, 1.5, 2.5),
    (D_B1,   'Block 1', '09:00–12:00 DEEP BUILD (phone in another room)',
             '19:30–21:00 one build block, post-shift',
             '14:00–16:30 DEEP BUILD (after sleep, before shift)'),
    (D_B2,   'Block 2', '13:00–15:30 BUILD #2 or outreach/admin', '—', '—'),
    (D_B3,   'Block 3', '19:00–19:45 admin + daily debrief', '21:00–21:15 debrief only',
             '16:30–16:45 debrief before shift'),
    (D_RULE, 'Rule', '2 deep blocks max — no third; stop while winning',
             'Do NOT plan more. 12h shift + 6h build = week-one burnout and a dead system',
             'Sleep ~07:00–13:30 is non-negotiable; the block comes after'),
]
for r, lbl, off, day, night in planner:
    is_num = isinstance(off, (int, float))
    put(f'B{r}', lbl, F_LBL, FILL_BAND, LFT, border=True)
    span(r, 'C', 'D', off, F_DAT, None, CTR if is_num else WRAP, '0.0' if is_num else None)
    span(r, 'E', 'F', day, F_DAT, None, CTR if is_num else WRAP, '0.0' if is_num else None)
    span(r, 'G', 'I', night, F_DAT, None, CTR if is_num else WRAP, '0.0' if is_num else None)
    ws.row_dimensions[r].height = 34
ws.row_dimensions[D_KEY].height = 18
ws.row_dimensions[D_TGT].height = 18
ws.row_dimensions[D_RULE].height = 40
span(D_CAS, 'B', 'I',
     'CASINO WINDOW — 30 min, ONLY between sprints (day 3 evening or before day 1): open the Parking Lot, '
     'research anything you want, timer on. When it rings, it’s over.',
     Font(name='Arial', size=9, bold=True, color=NAVY), FILL_BAND, LFT)
ws.row_dimensions[D_CAS].height = 28

# ---------------------------------------------------------------- BLOCK E
bar(E_BAR, 'PARKING LOT  ·  park it in 60 seconds, back to work')
header(E_HDR, [('B', 'Date'), ('C:E', 'The idea (one line)'), ('F:G', 'Why it feels urgent (one line)'),
               ('H:I', 'Earliest review: after Sprint #')])
for r in range(E_FIRST, E_LAST + 1):
    put(f'B{r}', None, F_DAT, FILL_IN, CTR, 'mmm dd yyyy', True)
    span(r, 'C', 'E', None, F_DAT, FILL_IN)
    span(r, 'F', 'G', None, F_DAT, FILL_IN)
    span(r, 'H', 'I', None, F_DAT, FILL_IN, CTR, '0')
    ws.row_dimensions[r].height = 16
span(E_NOTE, 'B', 'I',
     'Reviewed ONLY in the Casino Window. An idea that still looks good after 2 sprints in the lot has earned a '
     'real look. Most won’t.', F_NOTE, None, LFT, border=False)

# ---------------------------------------------------------------- BLOCK F
bar(F_BAR, 'SPRINT LOG  ·  the chain')
header(F_HDR, [('B', 'Sprint #'), ('C', 'Dates'), ('D:E', 'The demo'), ('F', 'Result ▾'),
               ('G', 'Proof (link / screenshot name / sent-to)'), ('H', 'Total hrs'), ('I', 'Chain')])
example = (0, 'Aug 21 → Aug 21', 'Sprint tab built and in the workbook   (example — delete)',
           'SHIPPED ✓', 'this tab', 2)
for r in range(F_FIRST, F_LAST + 1):
    ex = example if r == F_FIRST else (None,) * 6
    put(f'B{r}', ex[0], F_DAT, FILL_IN, CTR, '0', True)
    put(f'C{r}', ex[1], F_DAT, FILL_IN, CTR, None, True)
    span(r, 'D', 'E', ex[2], F_DAT, FILL_IN)
    put(f'F{r}', ex[3], F_DAT, FILL_IN, CTR, None, True)
    put(f'G{r}', ex[4], F_DAT, FILL_IN, WRAP, None, True)
    put(f'H{r}', ex[5], F_DAT, FILL_IN, CTR, '0.0', True)
    if r == F_FIRST:
        chain = f'=IF($F{r}="","",IF($F{r}="SHIPPED ✓",1,0))'
    else:
        chain = f'=IF($F{r}="","",IF($F{r}="SHIPPED ✓",N(I{r-1})+1,0))'
    put(f'I{r}', chain, F_DAT, None, CTR, '0', True)
    ws.row_dimensions[r].height = 16
span(F_NOTE, 'B', 'I',
     'No proof = not shipped. A document about the idea is not proof — the thing itself is.   '
     '"Chain" computes itself: consecutive SHIPPED ✓ rows.', F_NOTE, None, LFT, border=False)

# ---------------------------------------------------------------- BLOCK G
bar(G_BAR, 'NEXT UP  ·  pre-decided so day 1 is never "what should I do"')
header(G_HDR, [('B', '#'), ('C:D', 'Sprint'), ('E:I', 'The demo that ends it')])
queue = [
    ('Historical award pull',
     'CanadaBuys + BC Bid award history landed in Airtable. Demo = ranked shortlist table of candidate '
     'categories against the criteria ($10–40K lots, many winners, new entrants, no standing offer, '
     'no missing credential).'),
    ('Pipeline live',
     'n8n scheduled daily pull runs end-to-end unattended. Demo = screenshot of a successful scheduled run '
     '+ fresh rows landing.'),
    ('Gap-score engine',
     'Criteria scored automatically. Demo = top-3 nominated categories with scores, cross-checked against '
     'currently open tenders.'),
    ('Supplier registration',
     'Registered as a vendor on CanadaBuys / SAP Ariba (+ provincial equivalent). Demo = vendor confirmation.'),
    ('First bid',
     'Complete draft (or submission) on one live small tender in a nominated category. Demo = the bid document '
     '+ supplier quote request sent to the India contacts (payment-terms question finally answered by asking).'),
]
for i, (name, demo) in enumerate(queue):
    r = G_FIRST + i
    put(f'B{r}', i + 1, F_LBL, FILL_IN, CTR, '0', True)
    span(r, 'C', 'D', name, Font(name='Arial', size=9, bold=True), FILL_IN, LFT)
    span(r, 'E', 'I', demo, F_DAT, FILL_IN)
    ws.row_dimensions[r].height = 42

# ---------------------------------------------------------------- BLOCK H
bar(H_BAR, 'RULES  ·  read when the itch starts')
rules = [
    'One sprint. One demo. Defined before day 1. Never redefined mid-sprint.',
    'New idea → Parking Lot in 60 seconds → back to the block. Ideas are reviewed between sprints, never during.',
    'Ship ugly. A working embarrassment beats a polished plan.',
    'Research is not progress. If day 3’s artifact is a document *about* the idea, the sprint is not shipped.',
    '10-minute rule: you only ever commit to the first 10 minutes of a block. Start the timer.',
    'Day 3 ends with the demo sent to a human. Unsent = unshipped.',
    'Missed a sprint? The next one gets *smaller*. The system never gets abandoned, it gets easier.',
    'Killing a sprint costs a written kill row. Silent pivots don’t exist here.',
]
for i, text in enumerate(rules):
    r = H_FIRST + i
    put(f'B{r}', i + 1, F_LBL, None, CTR, '0', True)
    span(r, 'C', 'I', text, F_DAT, None, LFT)
    ws.row_dimensions[r].height = 18

# ---------------------------------------------------------------- validation lists (AA:AC, hidden)
put('AA1', 'Day type', F_NOTE)
for i, v in enumerate(['Off', 'Day shift', 'Night shift']):
    put(f'AA{2+i}', v, F_DAT)
put('AB1', 'Yes/No', F_NOTE)
for i, v in enumerate(['Yes', 'No']):
    put(f'AB{2+i}', v, F_DAT)
put('AC1', 'Status', F_NOTE)
for i, v in enumerate(['ACTIVE', 'SHIPPED ✓', 'KILLED ✗']):
    put(f'AC{2+i}', v, F_DAT)
put('AD1', '▲ dropdown source lists — hidden on purpose. Do not delete.', F_NOTE)
for col in ('AA', 'AB', 'AC'):
    ws.column_dimensions[col].hidden = True

dv_day = DataValidation(type='list', formula1='=$AA$2:$AA$4', allow_blank=True, showDropDown=False)
dv_yn  = DataValidation(type='list', formula1='=$AB$2:$AB$3', allow_blank=True, showDropDown=False)
dv_st  = DataValidation(type='list', formula1='=$AC$2:$AC$4', allow_blank=True, showDropDown=False)
for dv in (dv_day, dv_yn, dv_st):
    ws.add_data_validation(dv)
dv_day.add(f'D{C_D1}:D{C_D1+2}')
dv_yn.add(f'I{B_DONE1}:I{B_DONE3}')
dv_yn.add(f'G{C_D1}:G{C_D1+2}')
dv_st.add(f'C{B_STATUS}')
dv_st.add(f'F{F_FIRST}:F{F_LAST}')

# ---------------------------------------------------------------- conditional formats
def rule(text, color, bg):
    return CellIsRule(operator='equal', formula=[f'"{text}"'],
                      font=Font(name='Arial', size=9, bold=True, color=color),
                      fill=PatternFill('solid', bgColor=bg))

for rng in (f'C{B_STATUS}', f'F{F_FIRST}:F{F_LAST}'):
    ws.conditional_formatting.add(rng, rule('SHIPPED ✓', GREEN, 'C6EFCE'))
    ws.conditional_formatting.add(rng, rule('KILLED ✗', RED, LTRED))
    ws.conditional_formatting.add(rng, rule('ACTIVE', AMBER, 'FFEB9C'))
for rng in (f'I{B_DONE1}:I{B_DONE3}', f'G{C_D1}:G{C_D1+2}'):
    ws.conditional_formatting.add(rng, rule('Yes', GREEN, 'C6EFCE'))
    ws.conditional_formatting.add(rng, rule('No', RED, LTRED))
ws.conditional_formatting.add(
    f'C{B_LEFT}',
    CellIsRule(operator='equal', formula=['"SHIP DAY"'],
               font=Font(name='Arial', size=9, bold=True, color=AMBER),
               fill=PatternFill('solid', bgColor='FFEB9C')))
ws.conditional_formatting.add(
    f'C{B_LEFT}',
    CellIsRule(operator='containsText', formula=[f'NOT(ISERROR(SEARCH("OVERDUE",C{B_LEFT})))'],
               font=Font(name='Arial', size=9, bold=True, color=RED),
               fill=PatternFill('solid', bgColor=LTRED)))

# ---------------------------------------------------------------- move to index 0
wb.move_sheet('Sprint', offset=-(len(wb.sheetnames) - 1))
assert wb.sheetnames[0] == 'Sprint', wb.sheetnames
wb.save(OUT)
print('saved', OUT)
print(wb.sheetnames)
