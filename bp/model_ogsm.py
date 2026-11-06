"""Mô hình 2: OGSM cascade (Objective – Goals – Strategies – Measures)."""
from . import xl
from .actions import store_actions, supervisor_actions, tr
from .metrics import transfers

NAME = "M2_OGSM"
DESC = ("OGSM (P&G, Coca-Cola, Nestlé…): kế hoạch 1 trang. O = mục tiêu định tính; G = mục tiêu định lượng "
        "(target); S = 3–4 chiến lược/đòn bẩy; M = (a) dashboard đo lường từng chiến lược và (b) action plan có người "
        "phụ trách, hạn. Cascade: OGSM vùng của giám sát → OGSM từng cửa hàng.")

STRATS = [
    ("S1. Tăng lượt mua (số bill)", ("Số bill (lượt mua)",)),
    ("S2. Tăng giá trị bill (UPT × giá TB)", ("UPT (SP/bill)", "Giá TB/SP")),
    ("S3. Hàng hóa đúng – đủ – bán được", ("Hàng hóa",)),
    ("S4. Kỷ luật thực thi", ("Vận hành", "Doanh số")),
]


def _measures(s, b, key):
    if key.startswith("S1"):
        return [("Bill/tuần", s["bills28"] / 4, s["bills_tgt"], xl.INT), ("KH cũ có thể gọi lại", s["dormant"], min(s["dormant"], 140), xl.INT)]
    if key.startswith("S2"):
        return [("UPT", s["upt4"], s["upt_tgt"], xl.DEC2), ("Giá TB/SP", s["asp4"], s["asp_tgt"], xl.MONEY),
                ("ATV", s["atv4"], s["atv_tgt"], xl.MONEY), ("Tỷ trọng phụ kiện (SL)", s["addon_share"], None, xl.PCT)]
    if key.startswith("S3"):
        return [("SKU bán chạy sắp hết", len(s["rep"]), 0, xl.INT), ("Mẫu top chuỗi thiếu", len(s["miss"]), 0, xl.INT),
                ("SP tồn chậm", s["slow_units"], s["slow_units"] * 0.95, xl.INT), ("Cover toàn CH (ngày)", s["store_cover"], None, "0")]
    return [("Doanh số tuần", s["base_week"], s["week_target"], xl.MONEY), ("Số ngày cập nhật bảng điểm", 0, 7, xl.INT)]


def _ogsm_store(wb, ctx, s):
    ws = wb.create_sheet(xl.sheet_name(wb, s["name"]))
    b = ctx.bench
    r = xl.title(ws, f"OGSM – {s['name']}", f"GS {s['gs']} · Tuần {ctx.week_start:%d/%m}–{ctx.week_end:%d/%m/%Y} · Trạng thái: {s['rag']}")
    r = xl.section(ws, r, "O – OBJECTIVE", 9)
    ws.cell(r, 1, f"Đưa {s['name']} về đúng nhịp đạt 100% target tháng {ctx.week_start:%m/%Y}: "
                  "phục vụ thêm khách, mỗi bill nhiều sản phẩm hơn, hàng bán chạy luôn sẵn trên kệ.").alignment = xl.WRAP
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=9)
    ws.row_dimensions[r].height = 30
    r += 2
    r = xl.section(ws, r, "G – GOALS", 9)
    r, _ = xl.table(ws, r, ["Mục tiêu", "Hiện tại", "Chỉ tiêu", "Ghi chú"], [
        ["Doanh số tuần", s["base_week"], s["week_target"], "Hiện tại = TB 4 tuần"],
        ["Doanh số tháng", s["mtd"], s["target_month"], f"Dự báo {tr(s['forecast'])} ({s['ach_fc']:.0%})"],
        ["Số bill/tuần", s["bills28"] / 4, s["bills_tgt"], ""],
        ["ATV", s["atv4"], s["atv_tgt"], f"Trung vị chuỗi {tr(b['atv'])}"]],
        [None, xl.MONEY, xl.MONEY, None])
    for rr in (r - 3, r - 2):
        for c in "BC":
            ws[f"{c}{rr}"].number_format = xl.INT if rr == r - 3 else xl.MONEY
    acts = store_actions(s, ctx)
    for key, groups in STRATS:
        r = xl.section(ws, r, key, 9)
        ws.cell(r, 1, "M (dashboard)").font = xl.F_B
        r += 1
        r, f = xl.table(ws, r, ["Chỉ số", "Hiện tại", "Chỉ tiêu tuần", "Thực tế cuối tuần (nhập)"],
                        [[m[0], m[1], m[2], None] for m in _measures(s, b, key)])
        for i, m in enumerate(_measures(s, b, key)):
            for c in "BCD":
                ws[f"{c}{f + i}"].number_format = m[3]
        xl.input_cells(ws, f"D{f}:D{r - 2}")
        ws.cell(r, 1, "M (action plan)").font = xl.F_B
        r += 1
        r = xl.action_table(ws, r, [a for a in acts if a["nhom"] in groups])
    r = xl.section(ws, r, "Theo dõi ngày", 9)
    r = xl.daily_scoreboard(ws, r, s)
    r = xl.section(ws, r, "Phụ lục S3 – danh sách bổ sung hàng", 9)
    r = xl.sku_table(ws, r, s["rep"], "rep")
    r = xl.section(ws, r, "Phụ lục S3 – mẫu top chuỗi chưa có", 9)
    xl.sku_table(ws, r, s["miss"], "miss")
    xl.widths(ws, [26, 40, 14, 18, 12, 12, 10, 14, 24, 12])


def _ogsm_region(wb, ctx, gs, stores):
    ws = wb.create_sheet("OGSM vùng")
    T = sum(s["target_month"] for s in stores)
    W = sum(s["week_target"] for s in stores)
    r = xl.title(ws, f"OGSM VÙNG – GIÁM SÁT {gs.upper()} – TUẦN {ctx.week_label}",
                 f"Mô hình 2 · OGSM cascade · Số liệu bán đến {ctx.as_of:%d/%m/%Y}")
    r = xl.section(ws, r, "O – OBJECTIVE", 9)
    ws.cell(r, 1, f"Vùng {gs} đạt 100% target tháng {ctx.week_start:%m/%Y}, không cửa hàng nào dưới 85%.")
    r += 2
    r = xl.section(ws, r, "G – GOALS", 9)
    r, _ = xl.table(ws, r, ["Mục tiêu", "Hiện tại", "Chỉ tiêu"], [
        ["Doanh số tháng vùng", sum(s["mtd"] for s in stores), T],
        ["Doanh số tuần vùng", sum(s["base_week"] for s in stores), W],
        ["Số CH xanh (dự báo ≥100%)", sum(s["rag"] == "XANH" for s in stores), len(stores)],
        ["Số CH đỏ (dự báo <85%)", sum(s["rag"] == "ĐỎ" for s in stores), 0]], [None, xl.MONEY, xl.MONEY])
    for rr in (r - 3, r - 2):
        ws[f"B{rr}"].number_format = ws[f"C{rr}"].number_format = xl.INT
    r = xl.section(ws, r, "S – STRATEGIES & M – MEASURES theo cửa hàng", 9)
    rows = [[s["name"], s["rag"], s["week_target"], s["bills28"] / 4, s["bills_tgt"], s["upt4"], s["upt_tgt"],
             len(s["rep"]), s["slow_units"]] for s in sorted(stores, key=lambda x: x["ach_fc"])]
    r, _ = xl.table(ws, r, ["Cửa hàng", "Trạng thái", "G: Target tuần", "S1: Bill hiện tại", "S1: Bill mục tiêu",
                            "S2: UPT hiện tại", "S2: UPT mục tiêu", "S3: SKU cần bổ sung", "S3: SP tồn chậm"],
                    rows, [None, None, xl.MONEY, "#,##0", xl.INT, xl.DEC2, xl.DEC2, xl.INT, xl.INT])
    r = xl.section(ws, r, "M – Action plan của giám sát", 9)
    r = xl.action_table(ws, r, supervisor_actions(stores, ctx))
    tf = transfers(stores)
    r = xl.section(ws, r, "S3 – Điều chuyển trong vùng", 9)
    r, f = xl.table(ws, r, ["Từ CH", "Đến CH", "SKU", "Tên SP", "SL", "Trạng thái"],
                    [[t["tu"], t["den"], t["sku"], t["ten"], t["sl"], None] for t in tf])
    if tf:
        xl.status_col(ws, "F", f, f + len(tf) - 1)
    xl.widths(ws, [34, 14, 40, 14, 12, 12, 12, 14, 14])


def render(ctx, gs, stores, path):
    wb = xl.new_wb()
    _ogsm_region(wb, ctx, gs, stores)
    for s in sorted(stores, key=lambda x: x["name"]):
        _ogsm_store(wb, ctx, s)
    g = wb.create_sheet("Giải thích mô hình")
    g["A1"], g["A1"].font = "Mô hình 2 – OGSM", xl.F_TITLE
    g["A3"] = DESC
    g["A3"].alignment = xl.WRAP
    g.column_dimensions["A"].width = 120
    wb.save(path)
