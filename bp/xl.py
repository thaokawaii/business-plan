"""Helper ghi Excel (openpyxl)."""
import re

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

NAVY = "1F3864"
F_TITLE = Font(bold=True, size=14, color=NAVY)
F_H = Font(bold=True, color="FFFFFF")
F_B = Font(bold=True)
F_NOTE = Font(italic=True, size=9, color="666666")
FILL_H = PatternFill("solid", fgColor=NAVY)
FILL_SEC = PatternFill("solid", fgColor="D9E1F2")
FILL_IN = PatternFill("solid", fgColor="FFF2CC")   # ô nhập liệu
RAG_FILL = {"XANH": PatternFill("solid", fgColor="C6EFCE"), "VÀNG": PatternFill("solid", fgColor="FFEB9C"),
            "ĐỎ": PatternFill("solid", fgColor="FFC7CE")}
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")

MONEY = '#,##0.0,," tr"'
INT = "#,##0"
DEC2 = "0.00"
PCT = "0%"
DATE = "dd/mm"
STATUS = ["☐ Chưa làm", "◐ Đang làm", "☑ Hoàn thành", "✖ Không làm"]


def new_wb():
    wb = Workbook()
    wb.remove(wb.active)
    return wb


def sheet_name(wb, name):
    n = re.sub(r"[\[\]\:\*\?\/\\]", "-", name)[:31]
    base, i = n, 2
    while n in wb.sheetnames:
        n = f"{base[:28]}~{i}"
        i += 1
    return n


def title(ws, text, sub=None, row=1):
    ws.cell(row, 1, text).font = F_TITLE
    if sub:
        ws.cell(row + 1, 1, sub).font = F_NOTE
    return row + (3 if sub else 2)


def section(ws, row, text, width=8):
    for c in range(1, width + 1):
        ws.cell(row, c).fill = FILL_SEC
    ws.cell(row, 1, text).font = Font(bold=True, color=NAVY, size=12)
    return row + 1


def kv(ws, row, pairs, cols=4):
    """Khối chỉ số dạng nhãn/giá trị, `cols` cặp mỗi hàng. pairs: (label, value, fmt)."""
    for i, (lab, val, fmt) in enumerate(pairs):
        r, c = row + i // cols, 1 + (i % cols) * 2
        ws.cell(r, c, lab).font = F_NOTE
        cell = ws.cell(r, c + 1, val)
        cell.font = F_B
        if fmt:
            cell.number_format = fmt
        if isinstance(val, str) and val in RAG_FILL:
            cell.fill = RAG_FILL[val]
    return row + (len(pairs) + cols - 1) // cols + 1


def table(ws, row, headers, rows, fmts=None, widths=None, col=1):
    """Ghi bảng; fmts: list định dạng theo cột (hoặc None). Trả về (hàng kế tiếp, hàng đầu dữ liệu)."""
    for j, h in enumerate(headers):
        c = ws.cell(row, col + j, h)
        c.font, c.fill, c.border = F_H, FILL_H, BOX
        c.alignment = Alignment(wrap_text=True, vertical="center")
    first = row + 1
    for i, rr in enumerate(rows):
        for j, v in enumerate(rr):
            c = ws.cell(first + i, col + j, v)
            c.border = BOX
            c.alignment = WRAP
            if fmts and j < len(fmts) and fmts[j]:
                c.number_format = fmts[j]
            if isinstance(v, str) and v in RAG_FILL:
                c.fill = RAG_FILL[v]
    if not rows:
        ws.cell(first, col, "(không có)").font = F_NOTE
        return first + 2, first
    return first + len(rows) + 1, first


def status_col(ws, col_letter, r1, r2):
    """Cột trạng thái dạng dropdown + tô màu khi hoàn thành."""
    if r2 < r1:
        return
    dv = DataValidation(type="list", formula1='"' + ",".join(STATUS) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    rng = f"{col_letter}{r1}:{col_letter}{r2}"
    dv.add(rng)
    for r in range(r1, r2 + 1):
        ws[f"{col_letter}{r}"] = STATUS[0]
        ws[f"{col_letter}{r}"].fill = FILL_IN
    ws.conditional_formatting.add(rng, FormulaRule(formula=[f'LEFT({col_letter}{r1},1)="☑"'],
                                                   fill=PatternFill("solid", fgColor="C6EFCE")))
    ws.conditional_formatting.add(rng, FormulaRule(formula=[f'LEFT({col_letter}{r1},1)="◐"'],
                                                   fill=PatternFill("solid", fgColor="FFEB9C")))


def input_cells(ws, rng):
    for row in ws[rng]:
        for c in row:
            c.fill = FILL_IN


def pct_rule(ws, rng):
    ws.conditional_formatting.add(rng, CellIsRule(operator="greaterThanOrEqual", formula=["1"],
                                                  fill=PatternFill("solid", fgColor="C6EFCE")))
    ws.conditional_formatting.add(rng, CellIsRule(operator="between", formula=["0.85", "0.9999"],
                                                  fill=PatternFill("solid", fgColor="FFEB9C")))
    ws.conditional_formatting.add(rng, CellIsRule(operator="lessThan", formula=["0.85"],
                                                  fill=PatternFill("solid", fgColor="FFC7CE")))


def widths(ws, w):
    for i, x in enumerate(w, 1):
        ws.column_dimensions[get_column_letter(i)].width = x


def daily_scoreboard(ws, row, s, show_bills=True):
    """Bảng điểm ngày 4DX: target ngày + ô nhập thực tế, % và lũy kế tự tính."""
    hdr = ["Ngày", "Thứ", "Target ngày", "Thực tế (nhập)", "% đạt", "LK target", "LK thực tế", "Số bill (nhập)", "Số SP (nhập)", "UPT"]
    rows = [[d["date"], d["wd"], d["target"], None, None, None, None, None, None, None] for d in s["days"]]
    nxt, f = table(ws, row, hdr, rows, [DATE, None, MONEY, MONEY, PCT, MONEY, MONEY, INT, INT, DEC2])
    for i in range(7):
        r = f + i
        ws[f"E{r}"] = f'=IF(D{r}="","",D{r}/C{r})'
        ws[f"F{r}"] = f"=SUM(C${f}:C{r})"
        ws[f"G{r}"] = f'=IF(D{r}="","",SUM(D${f}:D{r}))'
        ws[f"J{r}"] = f'=IF(OR(H{r}="",H{r}=0),"",I{r}/H{r})'
    r = f + 7
    ws[f"A{r}"] = "Tổng tuần"
    ws[f"A{r}"].font = F_B
    ws[f"C{r}"] = f"=SUM(C{f}:C{f + 6})"
    ws[f"D{r}"] = f"=SUM(D{f}:D{f + 6})"
    ws[f"E{r}"] = f'=IF(D{r}=0,"",D{r}/C{r})'
    ws[f"H{r}"] = f"=SUM(H{f}:H{f + 6})"
    ws[f"I{r}"] = f"=SUM(I{f}:I{f + 6})"
    ws[f"J{r}"] = f'=IF(H{r}=0,"",I{r}/H{r})'
    for c, fm in zip("CDEHIJ", [MONEY, MONEY, PCT, INT, INT, DEC2]):
        ws[f"{c}{r}"].number_format = fm
        ws[f"{c}{r}"].font = F_B
        ws[f"{c}{r}"].border = BOX
    input_cells(ws, f"D{f}:D{f + 6}")
    input_cells(ws, f"H{f}:I{f + 6}")
    pct_rule(ws, f"E{f}:E{r}")
    return r + 2


def action_table(ws, row, actions, extra_cols=()):
    hdr = ["#", "Đòn bẩy", "Hành động", "KPI đo lường", "Chỉ tiêu", "Phụ trách", "Hạn", "Trạng thái", "Kết quả / ghi chú"]
    rows = [[i + 1, a["nhom"], a["viec"], a["kpi"], a["chi_tieu"], a["owner"], a["han"], None, None]
            for i, a in enumerate(actions)]
    nxt, f = table(ws, row, hdr, rows, [None, None, None, None, '#,##0.##', None, DATE, None, None])
    for i, a in enumerate(actions):
        if isinstance(a["chi_tieu"], float) and a["chi_tieu"] > 1e5:
            ws.cell(f + i, 5).number_format = MONEY
    if actions:
        status_col(ws, "H", f, f + len(actions) - 1)
        input_cells(ws, f"I{f}:I{f + len(actions) - 1}")
    return nxt


def sku_table(ws, row, df, kind):
    if kind == "rep":
        hdr = ["Mã SKU", "Tên SP", "Nhóm", "Bán 28N", "Tồn", "Đang về", "Cover (ngày)", "Kho tổng có", "Đề xuất bổ sung", "Trạng thái"]
        rows = [[x.productCode, x.fullName, x.categoryName, x.q28, x.qty_onhand, x.qty_incoming,
                 round(x.cover, 1), x.wh_avail, x.de_xuat, None] for x in df.itertuples()]
        fm = [None, None, None, INT, INT, INT, "0.0", INT, INT, None]
    elif kind == "slow":
        hdr = ["Mã SKU", "Tên SP", "Nhóm", "Tồn", "Bán 90N", "Bán lần cuối", "Hướng xử lý", "Trạng thái"]
        rows = [[x.productCode, x.fullName, x.categoryName, x.qty_onhand, x.q90, x.last_sold,
                 "Kệ đầu / KM / điều chuyển", None] for x in df.itertuples()]
        fm = [None, None, None, INT, INT, DATE, None, None]
    else:  # miss
        hdr = ["Mã SP (product_id)", "Tên mẫu bán chạy toàn chuỗi", "Bán 28N toàn chuỗi", "Trạng thái"]
        rows = [[int(i), x.ten, x.q28, None] for i, x in df.iterrows()]
        fm = [None, None, INT, None]
    nxt, f = table(ws, row, hdr, rows, fm)
    if rows:
        col = chr(ord("A") + len(hdr) - 1)
        status_col(ws, col, f, f + len(rows) - 1)
    return nxt
