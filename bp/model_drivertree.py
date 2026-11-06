"""Mô hình 1: Retail KPI Driver Tree + Gap-to-Target + nhịp 4DX."""
from . import xl
from .actions import store_actions, supervisor_actions, tr
from .metrics import transfers

NAME = "M1_DriverTree_4DX"
DESC = ("Doanh số = Số bill × ATV;  ATV = UPT × Giá TB/SP. Target tháng được phân bổ phần còn thiếu theo trọng số thứ "
        "trong tuần → target tuần/ngày. Gap giữa nền 4 tuần và target tuần được tách về từng driver; mỗi driver có "
        "lead measure + checklist. Nhịp 4DX: bảng điểm ngày, họp đầu ca, họp WIG tuần.")


def _overview(wb, ctx, gs, stores):
    ws = wb.create_sheet("Tổng quan vùng")
    r = xl.title(ws, f"BUSINESS PLAN TUẦN {ctx.week_label} – GIÁM SÁT {gs.upper()}",
                 f"Mô hình 1 · Driver Tree + 4DX · Tuần {ctx.week_start:%d/%m}–{ctx.week_end:%d/%m/%Y} · "
                 f"Số liệu bán đến {ctx.as_of:%d/%m/%Y}, tồn kho {ctx.inv_snapshot:%d/%m/%Y}")
    T = sum(s["target_month"] for s in stores)
    M = sum(s["mtd"] for s in stores)
    F = sum(s["forecast"] for s in stores)
    W = sum(s["week_target"] for s in stores)
    B = sum(s["base_week"] for s in stores)
    r = xl.kv(ws, r, [("Target tháng", T, xl.MONEY), ("Lũy kế tháng", M, xl.MONEY), ("% đạt", (M / T if T else 0), xl.PCT),
                      ("Dự báo cuối tháng", F, xl.MONEY), ("Target tuần", W, xl.MONEY), ("Nền 4 tuần/tuần", B, xl.MONEY),
                      ("Cần tăng", (W / B - 1) if B else 0, "+0%;-0%"), ("Số CH đỏ", sum(s["rag"] == "ĐỎ" for s in stores), xl.INT)])
    r = xl.section(ws, r, "Bảng xếp hạng cửa hàng (driver tree)", 18)
    hdr = ["Cửa hàng", "Trạng thái", "Target tháng", "Lũy kế", "% LK", "Dự báo", "% DB", "Cần/ngày", "TB 7N/ngày",
           "Target tuần", "Nền 4T/tuần", "Cần tăng", "Bill mục tiêu/tuần", "Bill TB/tuần", "UPT", "UPT mục tiêu",
           "Driver gap chính", "SKU cần bổ sung", "SKU tồn chậm"]
    rows = []
    for s in sorted(stores, key=lambda x: x["ach_fc"]):
        main = max(s["gap"], key=lambda k: s["gap"][k]) if s["gap"] else "-"
        rows.append([s["name"], s["rag"], s["target_month"], s["mtd"], s["ach_mtd"], s["forecast"], s["ach_fc"],
                     s["need_per_day"], s["avg7"], s["week_target"], s["base_week"], s["uplift"], s["bills_tgt"],
                     s["bills28"] / 4, s["upt4"], s["upt_tgt"], main, len(s["rep"]), s["slow_n"]])
    M_, P, I, D = xl.MONEY, xl.PCT, xl.INT, xl.DEC2
    r, f = xl.table(ws, r, hdr, rows, [None, None, M_, M_, P, M_, P, M_, M_, M_, M_, "+0%;-0%", I, "#,##0", D, D, None, I, I])
    xl.pct_rule(ws, f"G{f}:G{f + len(rows) - 1}")
    r = xl.section(ws, r, "Việc của giám sát tuần này", 18)
    r = xl.action_table(ws, r, supervisor_actions(stores, ctx))
    r = xl.section(ws, r, "Gợi ý điều chuyển hàng giữa các CH trong vùng (CH dư → CH thiếu)", 18)
    tf = transfers(stores)
    r, f = xl.table(ws, r, ["Từ CH", "Đến CH", "SKU", "Tên SP", "SL", "Trạng thái"],
                    [[t["tu"], t["den"], t["sku"], t["ten"], t["sl"], None] for t in tf])
    if tf:
        xl.status_col(ws, "F", f, f + len(tf) - 1)
    xl.widths(ws, [34, 10, 12, 12, 8, 12, 8, 11, 11, 12, 12, 9, 10, 10, 7, 8, 14, 9, 9])
    ws.freeze_panes = "B1"


def _store(wb, ctx, s):
    ws = wb.create_sheet(xl.sheet_name(wb, s["name"]))
    b = ctx.bench
    r = xl.title(ws, s["name"], f"GS {s['gs']} · {s['loai']} · {s['doitac']} · Tuần {ctx.week_start:%d/%m}–{ctx.week_end:%d/%m}")
    r = xl.kv(ws, r, [("Trạng thái", s["rag"], None), ("Target tháng", s["target_month"], xl.MONEY),
                      ("Lũy kế", s["mtd"], xl.MONEY), ("% LK", s["ach_mtd"], xl.PCT),
                      ("Dự báo cuối tháng", s["forecast"], xl.MONEY), ("% dự báo", s["ach_fc"], xl.PCT),
                      ("Cần/ngày còn lại", s["need_per_day"], xl.MONEY), ("TB 7 ngày qua", s["avg7"], xl.MONEY)])
    r = xl.section(ws, r, "WIG (Mục tiêu quan trọng nhất tuần)", 10)
    ws.cell(r, 1, f"Đạt {tr(s['week_target'])} doanh số tuần {ctx.week_label} = {s['bills_tgt']} bill × "
                  f"ATV {tr(s['atv_tgt'])} (UPT {s['upt_tgt']:.2f} × giá TB {tr(s['asp_tgt'])})").font = xl.F_B
    r += 2
    r = xl.section(ws, r, "Driver tree – hiện trạng vs mục tiêu tuần", 10)
    rows = [["Doanh số / tuần", s["rev7"], s["base_week"], None, s["week_target"], s["week_target"] / s["base_week"] - 1 if s["base_week"] else 0],
            ["  Số bill / tuần", s["bills7"], s["bills28"] / 4, None, s["bills_tgt"], s["bills_tgt"] / (s["bills28"] / 4) - 1 if s["bills28"] else 0],
            ["  ATV (giá trị bill)", s["atv7"], s["atv4"], b["atv"], s["atv_tgt"], s["atv_tgt"] / s["atv4"] - 1 if s["atv4"] else 0],
            ["    UPT (SP/bill)", s["upt7"], s["upt4"], b["upt"], s["upt_tgt"], s["upt_tgt"] / s["upt4"] - 1 if s["upt4"] else 0],
            ["    Giá TB/SP", s["rev7"] / s["units7"] if s["units7"] else 0, s["asp4"], b["asp"], s["asp_tgt"], s["asp_tgt"] / s["asp4"] - 1 if s["asp4"] else 0]]
    r, f = xl.table(ws, r, ["Chỉ số", "7 ngày qua", "TB 4 tuần", "Trung vị chuỗi", "Mục tiêu tuần", "Thay đổi cần"], rows)
    for i, fm in enumerate([xl.MONEY, xl.INT, xl.MONEY, xl.DEC2, xl.MONEY]):
        for c in "BCDE":
            ws[f"{c}{f + i}"].number_format = fm
        ws[f"F{f + i}"].number_format = "+0%;-0%"
    if s["gap"]:
        ws.cell(r - 1, 1, "Phân rã gap (tr): " + " · ".join(f"{k} {v / 1e6:+,.1f}" for k, v in s["gap"].items())).font = xl.F_NOTE
        r += 1
    r = xl.section(ws, r, "Bảng điểm ngày (nhập thực tế cuối ngày – ô vàng)", 10)
    r = xl.daily_scoreboard(ws, r, s)
    r = xl.section(ws, r, "Lead measures & checklist hành động", 10)
    r = xl.action_table(ws, r, store_actions(s, ctx))
    r = xl.section(ws, r, "Bổ sung hàng bán chạy sắp hết", 10)
    r = xl.sku_table(ws, r, s["rep"], "rep")
    r = xl.section(ws, r, "Mẫu bán chạy toàn chuỗi CH đang không có", 10)
    r = xl.sku_table(ws, r, s["miss"], "miss")
    r = xl.section(ws, r, f"Tồn chậm (có tồn, 0 bán 60 ngày) – {s['slow_n']} SKU / {s['slow_units']:,.0f} SP, top theo tồn", 10)
    xl.sku_table(ws, r, s["slow"], "slow")
    xl.widths(ws, [22, 40, 14, 14, 14, 14, 12, 12, 14, 22])


def render(ctx, gs, stores, path):
    wb = xl.new_wb()
    _overview(wb, ctx, gs, stores)
    for s in sorted(stores, key=lambda x: x["name"]):
        _store(wb, ctx, s)
    g = wb.create_sheet("Giải thích mô hình")
    g["A1"], g["A1"].font = "Mô hình 1 – Driver Tree + 4DX", xl.F_TITLE
    g["A3"] = DESC
    g["A3"].alignment = xl.WRAP
    g.column_dimensions["A"].width = 120
    wb.save(path)
