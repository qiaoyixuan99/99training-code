"""
Spare Parts ABC Classification Module (备件ABC等级分类模块)
==========================================================

Grade assignment based on composite Sum score:

  Sum = Q*0.1 + S*0.1 + V*0.2 + D*0.3 + P*0.3

Where:
  Q — Quality (质量)             weight: 0.1
  S — Safety (安全)              weight: 0.1
  V — Value (价格)               weight: 0.2
  D — Delivery (交期)            weight: 0.3
  P — Equipment importance (所在设备重要性) weight: 0.3

Classification thresholds:
  Sum > 4.5  →  Grade A (高优先级)
  2.5 < Sum <= 4.5  →  Grade B (中优先级)
  Sum <= 2.5  →  Grade C (低优先级)

Usage:
  from classify_parts import classify_by_sum, compute_sum

  grade = classify_by_sum(q=5, s=4, v=3, d=5, p=5)
  total = compute_sum(q=5, s=4, v=3, d=5, p=5)

CLI:
  python classify_parts.py <input.xlsx> <output.xlsx>
"""

# Sum weight coefficients
W_Q = 0.1  # Quality
W_S = 0.1  # Safety
W_V = 0.2  # Value
W_D = 0.3  # Delivery
W_P = 0.3  # Equipment importance

# Sum-based classification thresholds (user-defined)
THRESHOLD_AB = 4.5   # Sum > 4.5 → A
THRESHOLD_BC = 2.5   # Sum > 2.5 → B, else C


def compute_sum(q, s, v, d, p):
    """
    Compute weighted Sum score from the 5 evaluation factors.

    Args:
        q: Quality score (质量, 1-5)
        s: Safety score (安全, 1-5)
        v: Value score (价格, 1-5)
        d: Delivery score (交期, 1-5)
        p: Equipment importance score (所在设备重要性, 1-5)

    Returns:
        float: Sum = Q*0.1 + S*0.1 + V*0.2 + D*0.3 + P*0.3
    """
    return q * W_Q + s * W_S + v * W_V + d * W_D + p * W_P


def classify_by_sum(q, s, v, d, p):
    """
    Classify spare part into ABC grade based on composite Sum score.

    This is the PRIMARY function for new data entries.
    Computes Sum from the 5 factors and returns the corresponding grade.

    Rules:
        Sum > 4.5  →  A
        2.5 < Sum <= 4.5  →  B
        Sum <= 2.5  →  C

    Args:
        q: Quality score (1-5)
        s: Safety score (1-5)
        v: Value score (1-5)
        d: Delivery score (1-5)
        p: Equipment importance score (1-5)

    Returns:
        str: 'A', 'B', or 'C'

    Example:
        >>> classify_by_sum(q=5, s=5, v=5, d=5, p=5)  # Sum=5.0
        'A'
        >>> classify_by_sum(q=3, s=3, v=3, d=3, p=3)  # Sum=3.0
        'B'
        >>> classify_by_sum(q=1, s=1, v=1, d=1, p=1)  # Sum=1.0
        'C'
    """
    total = compute_sum(q, s, v, d, p)
    if total > THRESHOLD_AB:
        return 'A'
    elif total > THRESHOLD_BC:
        return 'B'
    else:
        return 'C'


def classify_with_detail(q, s, v, d, p):
    """
    Classify and return detailed breakdown.

    Args:
        q, s, v, d, p: The 5 evaluation factor scores (1-5)

    Returns:
        dict: {
            'sum': float,
            'grade': str,
            'q': int, 's': int, 'v': int, 'd': int, 'p': int,
        }
    """
    total = compute_sum(q, s, v, d, p)
    return {
        'sum': round(total, 2),
        'grade': classify_by_sum(q, s, v, d, p),
        'q': q, 's': s, 'v': v, 'd': d, 'p': p,
    }


# ============================================================
# Batch processing helper
# ============================================================
def process_excel(input_path, output_path):
    """
    Read an Excel file, compute Sum and ABC grade for each row,
    and save to a new file.

    Expects columns in Inventory sheet:
      AA(Q), AB(S), AC(V), AD(D), AE(P)
    Writes to:
      AF (Sum formula), L (Class/grade)
    """
    import openpyxl

    COL_CLASS = 12   # L
    COL_Q     = 27   # AA
    COL_S     = 28   # AB
    COL_V     = 29   # AC
    COL_D     = 30   # AD
    COL_P     = 31   # AE
    COL_SUM   = 32   # AF
    COL_MODEL = 8    # H

    wb = openpyxl.load_workbook(input_path)
    ws = wb['Inventory']

    count = 0
    empty_streak = 0
    for row_idx in range(2, ws.max_row + 1):
        model = ws.cell(row=row_idx, column=COL_MODEL).value
        if model is None:
            empty_streak += 1
            if empty_streak >= 200:
                break
            continue
        empty_streak = 0

        try:
            q = int(ws.cell(row=row_idx, column=COL_Q).value or 0)
            s = int(ws.cell(row=row_idx, column=COL_S).value or 0)
            v = int(ws.cell(row=row_idx, column=COL_V).value or 0)
            d = int(ws.cell(row=row_idx, column=COL_D).value or 0)
            p = int(ws.cell(row=row_idx, column=COL_P).value or 0)
        except (ValueError, TypeError):
            q = s = v = d = p = 1

        # Write Sum as Excel formula
        formula = f"=AA{row_idx}*0.1+AB{row_idx}*0.1+AC{row_idx}*0.2+AD{row_idx}*0.3+AE{row_idx}*0.3"
        ws.cell(row=row_idx, column=COL_SUM).value = formula

        # Write grade based on Sum
        grade = classify_by_sum(q, s, v, d, p)
        ws.cell(row=row_idx, column=COL_CLASS).value = grade
        count += 1

    wb.save(output_path)
    print(f"Processed {count} rows. Saved to: {output_path}")
    return count


# ============================================================
# Command-line entry point
# ============================================================
if __name__ == '__main__':
    import sys

    if len(sys.argv) >= 3:
        process_excel(sys.argv[1], sys.argv[2])
    else:
        print("ABC Classification Demo (Sum-based)")
        print("=" * 55)
        test_cases = [
            (5, 5, 5, 5, 5),
            (5, 5, 5, 5, 4),
            (4, 4, 4, 4, 4),
            (3, 3, 3, 3, 3),
            (2, 2, 2, 2, 2),
            (1, 1, 1, 1, 1),
            (5, 1, 5, 5, 5),
            (1, 5, 1, 1, 1),
            (3, 4, 5, 5, 5),
            (5, 3, 2, 2, 1),
        ]
        print(f"{'Q':>3} {'S':>3} {'V':>3} {'D':>3} {'P':>3}  {'Sum':>6}  {'Grade':>6}")
        print("-" * 45)
        for q, s, v, d, p in test_cases:
            result = classify_with_detail(q, s, v, d, p)
            print(f"{q:3} {s:3} {v:3} {d:3} {p:3}  {result['sum']:6.2f}  {result['grade']:>6}")
        print()
        print(f"Formula: Sum = Q*{W_Q} + S*{W_S} + V*{W_V} + D*{W_D} + P*{W_P}")
        print(f"Thresholds: Sum > {THRESHOLD_AB} → A, {THRESHOLD_BC} < Sum <= {THRESHOLD_AB} → B, Sum <= {THRESHOLD_BC} → C")
        print()
        print("Usage: python classify_parts.py <input.xlsx> <output.xlsx>")
