"""Mô hình 3: Merchandise / Open-to-Buy + vòng PDCA."""
import math

from . import xl
from .actions import tr
from .metrics import transfers

import config as C

NAME = "M3_Merch_OTB_PDCA"
DESC = ("Kế hoạch dẫn dắt bởi hàng hóa (chuẩn merchandise planning của các chuỗi thời trang/giày): "
        "kế hoạch bán theo nhóm hàng (đơn vị) từ target tuần, Open-to-Buy = Bán kế hoạch + Tồn mục tiêu − Tồn hiện có − Hàng đang về; "
        "đo sell-through, cover (ngày bán), tồn chậm, mẫu thiếu; điều chuyển nội vùng. Vận hành theo PDCA: "
        f"Plan (OTB) → Do (bổ sung/điều chuyển/đẩy tồn) → Check (bảng điểm, sell-through) → Act (điều chỉnh tuần sau). "
        f"Tồn mục tiêu = {C.TARGET_COVER_DAYS} ngày bán; cần bổ sung khi cover < {C.LOW_COVER_DAYS} ngày; tồn dư khi > {C.OVERSTOCK_COVER_DAYS} ngày.")


def _otb(s):
    cat = s["cat"].copy()
    units_plan = s["week_target"] / s["asp_tgt"] if s["asp_tgt"] else 0
    tot = cat["q28"].sum() or 1
    cat["plan_units"] = (cat["q28"] / tot * units_plan).round()
    cat["otb"] = (cat["plan_units"] + cat["q28"] / 28 * C.TARGET_COVER_DAYS - cat["onhand"] - cat["incoming"]).clip(lower=0).round()
    cat["excess"] = (cat["onhand"] - cat["q28"] / 28 * C.OVERSTOCK_COVER_DAYS).clip(lower=0).round()
    return cat, units_plan


def _store(wb, ctx, s, tf):
    ws = wb.create_sheet(xl.sheet_name(wb, s["name"]))
    cat, units_plan = _otb(s)
    r = xl.title(ws, f"MERCH PLAN – {s['name']}", f"GS {s['gs']} · Tuần {ctx.week_start:%d/%m}–{ctx.week_end:%d/%m/%Y} · Trạng thái: {s['rag']}")
    r = xl.kv(ws, r, [("Target tuần", s["week_target"], xl.MONEY), ("SL cần bán tuần", units_plan, xl.INT),
                      ("Tồn CH (SP)", s["onhand"], xl.INT), ("Cover CH (ngày)", s["store_cover"], "0"),
                      ("SKU có tồn", s["inv_skus"], xl.INT), ("ST% 28 ngày", s["units28"] / (s["units28"] + s["onhand"]) if s["units28"] + s["onhand"] else 0, xl.PCT),
                      ("SKU tồn chậm", s["slow_n"], xl.INT), ("SP tồn chậm", s["slow_units"], xl.INT)])
    r = xl.section(ws, r, "P – PLAN: kế hoạch bán & Open-to-Buy theo nhóm hàng", 12)
    rows = [[k, x.r28, x.q28, x.onhand, x.incoming, x.cover if x.cover < 9999 else None, x.st, x.plan_units, x.otb, x.excess,
             "BỔ SUNG" if x.otb > 0 and x.cover < C.LOW_COVER_DAYS * 2 else ("XẢ / ĐIỀU CHUYỂN" if x.excess > 0 else "OK")]
            for k, x in cat.iterrows()]
    r, f = xl.table(ws, r, ["Nhóm hàng", "Doanh số 28N", "Bán 28N", "Tồn", "Đang về", "Cover (ngày)", "Sell-through 28N",
                            "Kế hoạch bán tuần (SL)", "OTB – cần nhập (SL)", "Tồn dư (SL)", "Hành động"], rows,
                    [None, xl.MONEY, xl.INT, xl.INT, xl.INT, "0", xl.PCT, xl.INT, xl.INT, xl.INT, None])
    r = xl.section(ws, r, "D – DO: bổ sung SKU bán chạy sắp hết", 12)
    r = xl.sku_table(ws, r, s["rep"], "rep")
    r = xl.section(ws, r, "D – DO: nhận mẫu top chuỗi chưa có", 12)
    r = xl.sku_table(ws, r, s["miss"], "miss")
    r = xl.section(ws, r, "D – DO: điều chuyển liên quan cửa hàng", 12)
    mine = [t for t in tf if s["name"] in (t["tu"], t["den"])]
    r, f2 = xl.table(ws, r, ["Chiều", "CH đối tác", "SKU", "Tên SP", "SL", "Trạng thái"],
                     [["NHẬN" if t["den"] == s["name"] else "CHUYỂN ĐI", t["tu"] if t["den"] == s["name"] else t["den"],
                       t["sku"], t["ten"], t["sl"], None] for t in mine])
    if mine:
        xl.status_col(ws, "F", f2, f2 + len(mine) - 1)
    r = xl.section(ws, r, f"D – DO: đẩy hàng tồn chậm ({s['slow_n']} SKU / {s['slow_units']:,.0f} SP)", 12)
    r = xl.sku_table(ws, r, s["slow"], "slow")
    r = xl.section(ws, r, "C – CHECK: bảng điểm ngày", 12)
    r = xl.daily_scoreboard(ws, r, s)
    r = xl.section(ws, r, "C – CHECK: checklist hàng hóa trong tuần", 12)
    chk = [("Kiểm đếm hàng bán chạy đầu tuần, đối chiếu tồn hệ thống", "T2"),
           ("Gửi đề xuất bổ sung/OTB cho GS & kho tổng", "T2"),
           ("Nhận hàng, lên kệ trong 24h", "T4"),
           ("Đủ size cho các mẫu top 10 của CH", "T5"),
           ("Đổi layout: hàng tồn chậm ra kệ đầu/khu KM", "T3"),
           ("Đếm lại sell-through nhóm hàng chính", "CN")]
    r, f3 = xl.table(ws, r, ["#", "Việc", "Thời điểm", "Trạng thái", "Ghi chú"], [[i + 1, a, b, None, None] for i, (a, b) in enumerate(chk)])
    xl.status_col(ws, "D", f3, f3 + len(chk) - 1)
    r = xl.section(ws, r, "A – ACT: rút kinh nghiệm & điều chỉnh tuần sau (nhập)", 12)
    r, f4 = xl.table(ws, r, ["Điều gì hiệu quả", "Điều gì chưa hiệu quả", "Điều chỉnh tuần sau", "Phụ trách"], [[None] * 4 for _ in range(3)])
    xl.input_cells(ws, f"A{f4}:D{f4 + 2}")
    xl.widths(ws, [24, 40, 14, 12, 10, 12, 12, 14, 14, 12, 18])


def _overview(wb, ctx, gs, stores, tf):
    ws = wb.create_sheet("Tổng quan vùng")
    r = xl.title(ws, f"MERCH PLAN TUẦN {ctx.week_label} – GIÁM SÁT {gs.upper()}",
                 f"Mô hình 3 · Merchandise/OTB + PDCA · Bán đến {ctx.as_of:%d/%m/%Y}, tồn kho {ctx.inv_snapshot:%d/%m/%Y}")
    rows = []
    for s in sorted(stores, key=lambda x: x["store_cover"], reverse=True):
        st = s["units28"] / (s["units28"] + s["onhand"]) if s["units28"] + s["onhand"] else 0
        rows.append([s["name"], s["rag"], s["week_target"], s["onhand"], s["store_cover"], st, len(s["rep"]),
                     len(s["miss"]), s["slow_n"], s["slow_units"], s["slow_units"] / s["onhand"] if s["onhand"] else 0])
    r = xl.section(ws, r, "Sức khỏe tồn kho theo cửa hàng", 11)
    r, _ = xl.table(ws, r, ["Cửa hàng", "Trạng thái DS", "Target tuần", "Tồn (SP)", "Cover (ngày)", "ST% 28N",
                            "SKU cần bổ sung", "Mẫu top thiếu", "SKU tồn chậm", "SP tồn chậm", "% tồn chậm"], rows,
                    [None, None, xl.MONEY, xl.INT, "0", xl.PCT, xl.INT, xl.INT, xl.INT, xl.INT, xl.PCT])
    # Ma trận nhóm hàng vùng
    import pandas as pd
    allc = pd.concat([s["cat"][["q28", "r28", "onhand", "incoming"]] for s in stores]).groupby(level=0).sum()
    allc["cover"] = allc.apply(lambda x: x.onhand / (x.q28 / 28) if x.q28 else None, axis=1)
    allc["st"] = allc.apply(lambda x: x.q28 / (x.q28 + x.onhand) if x.q28 + x.onhand else 0, axis=1)
    allc = allc.sort_values("r28", ascending=False)
    r = xl.section(ws, r, "Nhóm hàng toàn vùng", 11)
    r, _ = xl.table(ws, r, ["Nhóm hàng", "Doanh số 28N", "Bán 28N", "Tồn", "Đang về", "Cover (ngày)", "ST% 28N"],
                    [[k, x.r28, x.q28, x.onhand, x.incoming, x.cover, x.st] for k, x in allc.iterrows()],
                    [None, xl.MONEY, xl.INT, xl.INT, xl.INT, "0", xl.PCT])
    r = xl.section(ws, r, f"Điều chuyển nội vùng đề xuất ({len(tf)} dòng)", 11)
    r, f = xl.table(ws, r, ["Từ CH", "Đến CH", "SKU", "Tên SP", "SL", "Trạng thái"],
                    [[t["tu"], t["den"], t["sku"], t["ten"], t["sl"], None] for t in tf])
    if tf:
        xl.status_col(ws, "F", f, f + len(tf) - 1)
    xl.widths(ws, [34, 30, 16, 40, 10, 12, 12, 12, 12, 12, 10])


def render(ctx, gs, stores, path):
    wb = xl.new_wb()
    tf = transfers(stores)
    _overview(wb, ctx, gs, stores, tf)
    for s in sorted(stores, key=lambda x: x["name"]):
        _store(wb, ctx, s, tf)
    g = wb.create_sheet("Giải thích mô hình")
    g["A1"], g["A1"].font = "Mô hình 3 – Merchandise / OTB + PDCA", xl.F_TITLE
    g["A3"] = DESC
    g["A3"].alignment = xl.WRAP
    g.column_dimensions["A"].width = 120
    wb.save(path)
