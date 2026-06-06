"""
Process over3.xlsx → over4.xlsx

Operations:
1. Read Inventory data rows
2. Regenerate Q(AA), S(AB), V(AC), D(AD), P(AE) as random integers 1-5
   (no constraint, uniform random — replaces the previous Sum > 4.5 constraint)
3. Write Excel formula for Sum in AF column:
   Sum = Q*0.1 + S*0.1 + V*0.2 + D*0.3 + P*0.3
4. Assign grade(L) based on Sum value:
   - Sum > 4.5  → A
   - 2.5 < Sum < 4.5  → B
   - Sum < 2.5  → C
5. Red fill on class cell if stock quantity < 2 (preserved behavior)
6. Save as over4.xlsx
"""
import openpyxl
from openpyxl.styles import PatternFill
import random

random.seed(42)  # reproducible results

SRC = r'd:\【99】training code\make money\1-库存管理\over3.xlsx'
DST = r'd:\【99】training code\make money\1-库存管理\over4.xlsx'

# Column indices (1-based)
COL_MODEL  = 8    # H  — Model
COL_CLASS  = 12   # L  — 等级 class
COL_ORIG   = 15   # O  — Original quantity
COL_QTY    = 16   # P  — Quantity
COL_UNIQUE = 26   # Z  — 唯一性 unique
COL_Q      = 27   # AA — 质量 Quality
COL_S      = 28   # AB — 安全 Safety
COL_V      = 29   # AC — 价格 Value
COL_D      = 30   # AD — 交期 Delivery
COL_P_EQ   = 31   # AE — 所在设备重要性 Equipment importance
COL_SUM    = 32   # AF — 分值 Sum

# Sum grade thresholds (explicit, user-defined)
# Sum > 4.5  → A
# 2.5 < Sum < 4.5  → B
# Sum < 2.5  → C
# Edge: Sum == 4.5 → B, Sum == 2.5 → C (strict inequality)

# ============================================================
# Phase 1: Read current data
# ============================================================
print("[1/4] Reading over3.xlsx...")

# Read computed qty values in data_only mode (P column has formulas)
wb_data = openpyxl.load_workbook(SRC, data_only=True)
ws_inv_data = wb_data['Inventory']

qty_lookup = {}
empty_streak = 0
for row_idx in range(2, ws_inv_data.max_row + 1):
    model = ws_inv_data.cell(row=row_idx, column=COL_MODEL).value
    qty = ws_inv_data.cell(row=row_idx, column=COL_QTY).value
    if model is not None:
        try:
            qty_lookup[row_idx] = float(qty) if qty is not None else 0.0
        except (ValueError, TypeError):
            qty_lookup[row_idx] = 0.0
        empty_streak = 0
    else:
        empty_streak += 1
        if empty_streak >= 200:
            break
wb_data.close()

# Load editable workbook
wb = openpyxl.load_workbook(SRC)
ws_inv = wb['Inventory']

inv_rows = []
empty_streak = 0
for row_idx in range(2, ws_inv.max_row + 1):
    model = ws_inv.cell(row=row_idx, column=COL_MODEL).value
    if model is not None:
        inv_rows.append({
            'row': row_idx,
            'model': str(model).strip(),
            'qty': qty_lookup.get(row_idx, 0.0),
        })
        empty_streak = 0
    else:
        empty_streak += 1
        if empty_streak >= 200:
            break

print(f"  Inventory data rows: {len(inv_rows)}")

# ============================================================
# Phase 2: Regenerate Q/S/V/D/P, compute Sum, assign grade
# ============================================================
print("\n[2/4] Regenerating Q/S/V/D/P (random 1-5) and assigning Sum-based grades...")

red_fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")

grade_counts = {'A': 0, 'B': 0, 'C': 0}

for info in inv_rows:
    row_idx = info['row']
    qty = info['qty']

    # Generate random 1-5 integers (uniform, no constraint)
    q_val = random.randint(1, 5)
    s_val = random.randint(1, 5)
    v_val = random.randint(1, 5)
    d_val = random.randint(1, 5)
    p_val = random.randint(1, 5)

    # Compute Sum
    sum_val = q_val * 0.1 + s_val * 0.1 + v_val * 0.2 + d_val * 0.3 + p_val * 0.3

    # Grade by Sum value
    if sum_val > 4.5:
        grade = 'A'
    elif sum_val > 2.5:
        grade = 'B'
    else:
        grade = 'C'

    grade_counts[grade] += 1

    # Write integer values
    ws_inv.cell(row=row_idx, column=COL_UNIQUE).value = 0
    ws_inv.cell(row=row_idx, column=COL_Q).value = q_val
    ws_inv.cell(row=row_idx, column=COL_S).value = s_val
    ws_inv.cell(row=row_idx, column=COL_V).value = v_val
    ws_inv.cell(row=row_idx, column=COL_D).value = d_val
    ws_inv.cell(row=row_idx, column=COL_P_EQ).value = p_val

    # Excel formula for Sum (live recalculation)
    formula = f"=AA{row_idx}*0.1+AB{row_idx}*0.1+AC{row_idx}*0.2+AD{row_idx}*0.3+AE{row_idx}*0.3"
    ws_inv.cell(row=row_idx, column=COL_SUM).value = formula

    # Write grade FORMULA to L column (so it auto-updates when Sum changes)
    # IF(AF>4.5,"A", IF(AF>2.5,"B","C"))
    grade_formula = f'=IF(AF{row_idx}>4.5,"A",IF(AF{row_idx}>2.5,"B","C"))'
    class_cell = ws_inv.cell(row=row_idx, column=COL_CLASS)
    class_cell.value = grade_formula

    # Red fill if stock quantity < 2
    if qty < 2:
        class_cell.fill = red_fill

print(f"  Grade distribution: A={grade_counts['A']}, B={grade_counts['B']}, C={grade_counts['C']}")

# ============================================================
# Phase 3: Write SumThresholds reference sheet
# ============================================================
print("\n[3/4] Writing SumThresholds reference sheet...")

THRESHOLD_AB = 4.5
THRESHOLD_BC = 2.5

if 'SumThresholds' in wb.sheetnames:
    del wb['SumThresholds']
ws_thresh = wb.create_sheet('SumThresholds')
ws_thresh['A1'] = 'Grade'
ws_thresh['B1'] = 'Sum Range'
ws_thresh['A2'] = 'A'
ws_thresh['B2'] = 'Sum > 4.5'
ws_thresh['A3'] = 'B'
ws_thresh['B3'] = '2.5 < Sum <= 4.5'
ws_thresh['A4'] = 'C'
ws_thresh['B4'] = 'Sum <= 2.5'
ws_thresh['A6'] = 'Formula'
ws_thresh['B6'] = 'Sum = Q*0.1 + S*0.1 + V*0.2 + D*0.3 + P*0.3'
ws_thresh['A7'] = 'Note'
ws_thresh['B7'] = 'Grade is determined by Sum (composite score), NOT by the Safety column alone.'

# ============================================================
# Phase 4: Save
# ============================================================
print(f"\n[4/4] Saving to: {DST}")
wb.save(DST)
print("Done! over4.xlsx created successfully.")
