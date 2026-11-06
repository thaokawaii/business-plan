"""Mô hình KẾT HỢP: OGSM (khung chiến lược) → Driver Tree + 4DX (thực thi S1, S2, S4) → OTB + PDCA (thực thi S3).

Mỗi giám sát 1 file:
  - Hướng dẫn         : cách đọc & nhịp làm việc
  - OGSM vùng         : O, G, S1–S4 × cửa hàng, việc của GS
  - Điều hành bán hàng: bảng xếp hạng driver tree các CH
  - Hàng hóa vùng     : sức khỏe tồn kho, nhóm hàng, điều chuyển
  - 1 sheet / cửa hàng: ① OGSM CH → ② Bán hàng (S1,S2,S4) → ③ Hàng hóa (S3) → ④ Đánh giá tuần
"""
import pandas as pd

import config as C

from . import xl
from .actions import store_actions, supervisor_actions, tr

NAME = "KET_HOP_OGSM_4DX_OTB"

S_NAME = {
    "S1": "S1. Tăng lượt mua (số bill)",
    "S2": "S2. Tăng giá trị bill (UPT × giá TB)",
    "S3": "S3. Hàng hóa đúng – đủ – bán được",
    "S4": "S4. Kỷ luật thực thi",
}
S_TOOL = {"S1": "Driver Tree + 4DX (mục ②)", "S2": "Driver Tree + 4DX (mục ②)",
          "S3": "OTB + PDCA (mục ③)", "S4": "4DX: bảng điểm & họp (mục ②, ④)"}
NHOM_TO_S = {"Số bill (lượt mua)": "S1", "UPT (SP/bill)": "S2", "Giá TB/SP": "S2",
             "Hàng hóa": "S3", "Vận hành": "S4", "Doanh số": "S4", "Ưu tiên": "S4"}


def _tag(actions):
    """Gắn mã chiến lược vào cột đòn bẩy: 'S1 · Số bill (lượt mua)'."""
    out = []
    for a in actions:
        a = dict(a)
        a["s"] = NHOM_TO_S.get(a["nhom"], "S4")
        a["nhom"] = f"{a['s']} · {a['nhom']}"
        out.append(a)
    return out


def _st(s):
    return s["units28"] / (s["units28"] + s["onhand"]) if s["units28"] + s["onhand"] else 0


def _otb(s):
    cat = s["cat"].copy()
    units_plan = s["week_target"] / s["asp_tgt"] if s["asp_tgt"] else 0
    tot = cat["q28"].sum() or 1
    cat["plan_units"] = (cat["q28"] / tot * units_plan).round()
    cat["otb"] = (cat["plan_units"] + cat["q28"] / 28 * C.TARGET_COVER_DAYS - cat["onhand"] - cat["incoming"]).clip(lower=0).round()
    cat["excess"] = (cat["onhand"] - cat["q28"] / 28 * C.OVERSTOCK_COVER_DAYS).clip(lower=0).round()
    return cat, units_plan


# ---------------------------------------------------------------- vùng
def _guide(wb, ctx, gs):
    ws = wb.create_sheet("Hướng dẫn")
    r = xl.title(ws, f"BUSINESS PLAN TUẦN {ctx.week_label} – GIÁM SÁT {gs.upper()}",
                 f"Mô hình kết hợp OGSM + Driver Tree/4DX + OTB/PDCA · Tuần {ctx.week_start:%d/%m}–{ctx.week_end:%d/%m/%Y} · "
                 f"Bán hàng đến {ctx.as_of:%d/%m/%Y}, tồn kho {ctx.inv_snapshot:%d/%m/%Y}")
    r = xl.section(ws, r, "Cấu trúc mô hình", 6)
    r, _ = xl.table(ws, r, ["Tầng", "Mô hình", "Trả lời câu hỏi", "Nằm ở đâu trong file"], [
        ["Chiến lược", "OGSM", "Đi đâu? Thắng bằng 4 chiến lược nào? Đo bằng gì?", "Sheet 'OGSM vùng' + mục ① mỗi CH"],
        ["Thực thi bán hàng", "Driver Tree + 4DX", "Thiếu target do bill, UPT hay giá? Mỗi ngày làm gì? (S1, S2, S4)",
         "Sheet 'Điều hành bán hàng' + mục ② mỗi CH"],
        ["Thực thi hàng hóa", "OTB + PDCA", "Cần nhập mẫu nào (đủ size), xả gì, mùa vụ & sự kiện nào? (S3)", "Sheet 'Hàng hóa vùng' + mục ③ mỗi CH"],
        ["Cải tiến", "PDCA (Act) + họp WIG", "Tuần qua chiến lược nào hiệu quả, tuần sau đổi gì?", "Mục ④ mỗi CH"]])
    r = xl.section(ws, r, "Nhịp làm việc trong tuần", 6)
    r, _ = xl.table(ws, r, ["Thời điểm", "Ai", "Việc", "Dùng phần nào"], [
        ["Thứ Hai sáng", "GS + CHT", "Họp WIG 20': xem OGSM CH, driver tree, chốt cam kết tuần", "① ② ④ (tuần trước)"],
        ["Thứ Hai", "CHT → GS", "Kiểm đếm hàng bán chạy, gửi đề xuất bổ sung/OTB; GS duyệt đề xuất mẫu đủ size & xử lý size lẻ", "③ + Hàng hóa vùng"],
        ["Mỗi sáng", "CHT + NV", "Họp đầu ca 10': bảng điểm hôm qua, 1 cam kết/người", "② Bảng điểm ngày"],
        ["Mỗi tối", "CHT", "Nhập thực tế, số bill, số SP; cập nhật trạng thái checklist", "② ③ (ô vàng, cột Trạng thái)"],
        ["T3–T5", "CHT", "Nhận hàng lên kệ 24h, đổi layout tồn chậm, đủ size mẫu top", "③ Checklist hàng hóa"],
        ["Chủ nhật", "CHT", "Nhập thực tế cuối tuần cho G/S, ghi đánh giá", "① cột Thực tế, ④"],
        ["Chủ nhật", "GS", "Tổng hợp vùng, chuẩn bị họp tuần sau, báo cáo cấp trên", "OGSM vùng"]])
    r = xl.section(ws, r, "Quy ước", 6)
    for t in ["Ô nền vàng = ô cửa hàng nhập liệu. Cột 'Trạng thái' chọn ☐ Chưa làm / ◐ Đang làm / ☑ Hoàn thành / ✖ Không làm.",
              "Trạng thái CH: XANH dự báo ≥100% target tháng, VÀNG 85–100%, ĐỎ <85%. Dự báo = lũy kế + nhịp TB 28 ngày.",
              "Target tuần/ngày = phần target tháng còn thiếu chia cho các ngày còn lại theo trọng số thứ (T7–CN cao hơn).",
              f"Hàng hóa: tồn mục tiêu {C.TARGET_COVER_DAYS} ngày bán; bổ sung khi cover < {C.LOW_COVER_DAYS} ngày; "
              f"tồn chậm = không bán {C.SLOW_MOVER_DAYS} ngày; tồn dư khi cover > {C.OVERSTOCK_COVER_DAYS} ngày.",
              "Mã S1–S4 ở cột 'Đòn bẩy' cho biết hành động phục vụ chiến lược nào trong OGSM.",
              "Số liệu bán hàng chỉ tính kênh POS (bán tại quầy).",
              "Hàng hóa: KHÔNG chuyển lẻ size giữa cửa hàng. Gợi ý ở cấp MẪU-MÀU đủ dải size, dựa trên CH cùng khu vực, "
              "xu hướng nhóm hàng theo khu vực, mùa vụ và lịch sự kiện. GS là người quyết định."]:
        ws.cell(r, 1, "• " + t).alignment = xl.WRAP
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
        ws.row_dimensions[r].height = 30
        r += 1
    xl.widths(ws, [18, 22, 60, 36])


def _ogsm_region(wb, ctx, gs, stores):
    ws = wb.create_sheet("OGSM vùng")
    T = sum(s["target_month"] for s in stores)
    M = sum(s["mtd"] for s in stores)
    F = sum(s["forecast"] for s in stores)
    W = sum(s["week_target"] for s in stores)
    B = sum(s["base_week"] for s in stores)
    r = xl.title(ws, f"OGSM VÙNG – GIÁM SÁT {gs.upper()} – TUẦN {ctx.week_label}",
                 f"Tuần {ctx.week_start:%d/%m}–{ctx.week_end:%d/%m/%Y} · Bán hàng đến {ctx.as_of:%d/%m/%Y}")
    r = xl.section(ws, r, "O – OBJECTIVE", 12)
    ws.cell(r, 1, f"Vùng {gs} đạt 100% target tháng {ctx.week_start:%m/%Y}, không cửa hàng nào dưới 85%, "
                  "hàng bán chạy luôn đủ trên kệ.").font = xl.F_B
    r += 2
    r = xl.section(ws, r, "G – GOALS", 12)
    r, f = xl.table(ws, r, ["Mục tiêu", "Hiện tại", "Chỉ tiêu", "Ghi chú"], [
        ["Doanh số tháng vùng", M, T, f"Dự báo {tr(F)} ({F / T:.0%})" if T else ""],
        ["Doanh số tuần vùng", B, W, "Hiện tại = TB 4 tuần"],
        ["Số CH xanh", sum(s["rag"] == "XANH" for s in stores), len(stores), ""],
        ["Số CH đỏ", sum(s["rag"] == "ĐỎ" for s in stores), 0, ""]], [None, xl.MONEY, xl.MONEY, None])
    for rr in (f + 2, f + 3):
        ws[f"B{rr}"].number_format = ws[f"C{rr}"].number_format = xl.INT
    r = xl.section(ws, r, "S – STRATEGIES × M – MEASURES theo cửa hàng (hiện tại → mục tiêu tuần)", 12)
    rows = [[s["name"], s["rag"], s["ach_fc"], s["week_target"],
             s["bills28"] / 4, s["bills_tgt"], s["upt4"], s["upt_tgt"],
             len(s["rep"]), len(s["miss"]), s["slow_units"], None]
            for s in sorted(stores, key=lambda x: x["ach_fc"])]
    r, f = xl.table(ws, r, ["Cửa hàng", "Trạng thái", "% dự báo", "G: Target tuần",
                            "S1: Bill/tuần", "S1: Bill mục tiêu", "S2: UPT", "S2: UPT mục tiêu",
                            "S3: SKU cần bổ sung", "S3: Mẫu top thiếu", "S3: SP tồn chậm", "S4: Số ngày nhập bảng điểm (nhập)"],
                    rows, [None, None, xl.PCT, xl.MONEY, "#,##0", xl.INT, xl.DEC2, xl.DEC2, xl.INT, xl.INT, xl.INT, xl.INT])
    xl.pct_rule(ws, f"C{f}:C{f + len(rows) - 1}")
    xl.input_cells(ws, f"L{f}:L{f + len(rows) - 1}")
    r = xl.section(ws, r, "M – Action plan của giám sát", 12)
    xl.action_table(ws, r, _tag(supervisor_actions(stores, ctx)))
    xl.widths(ws, [34, 14, 46, 14, 12, 12, 10, 12, 12, 12, 12, 16])
    ws.freeze_panes = "B1"


def _sales_region(wb, ctx, stores):
    ws = wb.create_sheet("Điều hành bán hàng")
    b = ctx.bench
    r = xl.title(ws, "ĐIỀU HÀNH BÁN HÀNG – DRIVER TREE (S1, S2)",
                 f"Trung vị chuỗi 28 ngày: ATV {tr(b['atv'])} · UPT {b['upt']:.2f} · Giá TB/SP {tr(b['asp'])}")
    hdr = ["Cửa hàng", "Trạng thái", "Target tháng", "Lũy kế", "% LK", "Dự báo", "% DB", "Cần/ngày", "TB 7N/ngày",
           "Target tuần", "Nền 4T/tuần", "Cần tăng", "Bill mục tiêu/tuần", "Bill TB/tuần", "UPT", "UPT mục tiêu",
           "ATV", "Giá TB/SP", "Driver gap chính"]
    rows = []
    for s in sorted(stores, key=lambda x: x["ach_fc"]):
        main = max(s["gap"], key=lambda k: s["gap"][k]) if s["gap"] else "-"
        rows.append([s["name"], s["rag"], s["target_month"], s["mtd"], s["ach_mtd"], s["forecast"], s["ach_fc"],
                     s["need_per_day"], s["avg7"], s["week_target"], s["base_week"], s["uplift"], s["bills_tgt"],
                     s["bills28"] / 4, s["upt4"], s["upt_tgt"], s["atv4"], s["asp4"], main])
    M_, P, I, D = xl.MONEY, xl.PCT, xl.INT, xl.DEC2
    r, f = xl.table(ws, r, hdr, rows, [None, None, M_, M_, P, M_, P, M_, M_, M_, M_, "+0%;-0%", I, "#,##0", D, D, M_, M_, None])
    xl.pct_rule(ws, f"G{f}:G{f + len(rows) - 1}")
    xl.widths(ws, [34, 10, 12, 12, 8, 12, 8, 11, 11, 12, 12, 9, 10, 10, 7, 8, 11, 11, 14])
    ws.freeze_panes = "B4"


def _events(ws, r, ctx, width=10):
    r = xl.section(ws, r, f"Lịch sự kiện {C.EVENT_LOOKAHEAD_DAYS} ngày tới (DS chuỗi POS ngày sự kiện ±1 so với TB cùng thứ 4 tuần trước)", width)
    r, _ = xl.table(ws, r, ["Ngày", "Sự kiện", "Gợi ý hàng hóa/hoạt động", "Hiệu ứng lần gần nhất", "Tham chiếu"],
                    [[e["date"], e["name"], e["hint"], e["uplift"], e["ref"]] for e in ctx.events],
                    [xl.DATE, None, None, '0.00"x"', None])
    if ctx.event_hist:
        ws.cell(r - 1, 1, "Đã đo: " + " · ".join(f"{h['name']} {h['date']:%d/%m} ×{h['uplift']:.2f}" for h in ctx.event_hist)).font = xl.F_NOTE
        r += 1
    return r


def _merch_region(wb, ctx, stores):
    ws = wb.create_sheet("Hàng hóa vùng")
    r = xl.title(ws, "HÀNG HÓA VÙNG – OTB + PDCA (S3)",
                 f"Tồn kho {ctx.inv_snapshot:%d/%m/%Y} · Bán POS đến {ctx.as_of:%d/%m/%Y} · Không chuyển lẻ size – gợi ý cấp mẫu đủ size")
    r = xl.section(ws, r, "Sức khỏe tồn kho & đặc tính cửa hàng (tồn nặng nhất lên đầu)", 12)
    rows = [[s["name"], s["profile"]["region"], s["rag"], s["onhand"], s["store_cover"], _st(s),
             s["profile"]["price_tier"], s["profile"]["women_share"], s["profile"]["core_sizes"],
             len(s["style_requests"]), s["broken_n"], s["broken_units"], s["slow_units"]]
            for s in sorted(stores, key=lambda x: x["store_cover"], reverse=True)]
    r, _ = xl.table(ws, r, ["Cửa hàng", "Khu vực", "Trạng thái DS", "Tồn (SP)", "Cover (ngày)", "ST% 28N",
                            "Mức giá vs chuỗi", "% hàng nữ", "Size bán chạy", "Mẫu đề xuất nhận",
                            "Mẫu size lẻ", "SP size lẻ", "SP tồn chậm"], rows,
                    [None, None, None, xl.INT, "0", xl.PCT, "0.00", xl.PCT, None, xl.INT, xl.INT, xl.INT, xl.INT])
    regions = sorted({s["region"] for s in stores})
    for reg in regions:
        t = ctx.region_trend.get(reg)
        if t is None:
            continue
        r = xl.section(ws, r, f"Xu hướng nhóm hàng – {C.REGIONS.get(reg, reg)} (28N gần nhất vs 28N trước) · "
                              f"Mùa vụ: {region_climate(reg, ctx)}", 12)
        rows = [[k, x.q28, x.share, x.growth] for k, x in t.head(15).iterrows()]
        r, f = xl.table(ws, r, ["Nhóm hàng", "Bán 28N (SL)", "Tỷ trọng", "Tăng/giảm"], rows, [None, xl.INT, xl.PCT, "+0%;-0%"])
    r = _events(ws, r, ctx, 12)
    rot = [(s["name"], x) for s in stores for x in s["rotations"]]
    r = xl.section(ws, r, f"Gợi ý luân chuyển NGUYÊN MẪU (đủ size, CH không bán 60N, khu vực khác đang bán) – GS quyết định ({len(rot)})", 12)
    r, f = xl.table(ws, r, ["CH đang giữ", "Mẫu – màu", "Nhóm", "Số size", "SL", "Khu vực bán tốt", "Bán 28N ở đó",
                            "Xu hướng nhóm ở đó", "Quyết định"],
                    [[n, x["style"], x["cat"], x["n_sizes"], x["units"], x["to_region"], x["to_q28"], x["to_growth"], None] for n, x in rot],
                    [None, None, None, xl.INT, xl.INT, None, xl.INT, "+0%;-0%", None])
    if rot:
        xl.status_col(ws, "I", f, f + len(rot) - 1)
    xl.widths(ws, [34, 44, 16, 12, 10, 14, 12, 10, 14, 12, 10, 10, 10])


def region_climate(reg, ctx):
    from .insights import climate_note
    return climate_note(reg, ctx.week_start.month) or "-"


# ---------------------------------------------------------------- cửa hàng
def _store(wb, ctx, s):
    ws = wb.create_sheet(xl.sheet_name(wb, s["name"]))
    b = ctx.bench
    acts = _tag(store_actions(s, ctx))
    r = xl.title(ws, s["name"], f"GS {s['gs']} · {s['loai']} · {s['doitac']} · Tuần {ctx.week_start:%d/%m}–{ctx.week_end:%d/%m/%Y}")
    r = xl.kv(ws, r, [("Trạng thái", s["rag"], None), ("Target tháng", s["target_month"], xl.MONEY),
                      ("Lũy kế", s["mtd"], xl.MONEY), ("% LK", s["ach_mtd"], xl.PCT),
                      ("Dự báo cuối tháng", s["forecast"], xl.MONEY), ("% dự báo", s["ach_fc"], xl.PCT),
                      ("Target tuần", s["week_target"], xl.MONEY), ("Cần/ngày còn lại", s["need_per_day"], xl.MONEY)])

    p = s["profile"]
    r = xl.section(ws, r, "Đặc tính cửa hàng – địa lý · khách hàng · mùa vụ", 10)
    cb = p["combo"]
    r = xl.kv(ws, r, [("Khu vực", p["region"], None), ("Loại mặt bằng", p["archetype"], None),
                      ("Mức giá vs chuỗi", p["price_tier"] or 0, "0.00\"x\""), ("% hàng nữ (90N)", p["women_share"], xl.PCT),
                      ("% phụ kiện (SL)", p["addon_share"], xl.PCT), ("Size bán chạy", p["core_sizes"], None),
                      ("UPT bill combo / thường", f"{cb[0]:.1f} / {cb[1]:.1f}" if cb else "-", None),
                      ("% bill combo", cb[2] if cb else 0, xl.PCT)])
    ws.cell(r - 1, 1, f"Mùa vụ: {p['climate'] or '-'}  ·  So sánh với: {p['peer_scope']}").font = xl.F_NOTE
    r += 1

    # ① OGSM
    r = xl.section(ws, r, "① OGSM CỬA HÀNG – chiến lược tuần", 10)
    ws.cell(r, 1, "O").font = xl.F_B
    ws.cell(r, 2, f"Đạt 100% target tháng {ctx.week_start:%m/%Y}: phục vụ thêm khách, mỗi bill nhiều SP hơn, "
                  "hàng bán chạy luôn sẵn trên kệ.")
    r += 1
    ws.cell(r, 1, "WIG tuần").font = xl.F_B
    ws.cell(r, 2, f"{tr(s['week_target'])} = {s['bills_tgt']} bill × ATV {tr(s['atv_tgt'])} "
                  f"(UPT {s['upt_tgt']:.2f} × giá TB {tr(s['asp_tgt'])})").font = xl.F_B
    r += 2
    g_rows = [
        ["G", "Doanh số tuần", s["base_week"], s["week_target"], None, "Bảng điểm ngày (②)"],
        [S_NAME["S1"], "Số bill/tuần", s["bills28"] / 4, s["bills_tgt"], None, S_TOOL["S1"]],
        [S_NAME["S2"], "UPT", s["upt4"], s["upt_tgt"], None, S_TOOL["S2"]],
        ["", "ATV", s["atv4"], s["atv_tgt"], None, ""],
        [S_NAME["S3"], "SKU bán chạy sắp hết", len(s["rep"]), 0, None, S_TOOL["S3"]],
        ["", "SP tồn chậm", s["slow_units"], round(s["slow_units"] * 0.95), None, ""],
        [S_NAME["S4"], "Số ngày nhập bảng điểm", 0, 7, None, S_TOOL["S4"]],
    ]
    fm = [xl.MONEY, "#,##0", xl.DEC2, xl.MONEY, xl.INT, xl.INT, xl.INT]
    r, f = xl.table(ws, r, ["Chiến lược", "M – Chỉ số đo", "Hiện tại", "Mục tiêu tuần", "Thực tế cuối tuần (nhập)", "Công cụ thực thi"], g_rows)
    for i, x in enumerate(fm):
        for c in "CDE":
            ws[f"{c}{f + i}"].number_format = x
    xl.input_cells(ws, f"E{f}:E{f + len(g_rows) - 1}")

    # ② Bán hàng
    r = xl.section(ws, r, "② THỰC THI BÁN HÀNG – Driver Tree + 4DX (S1, S2, S4)", 10)
    rows = [["Doanh số / tuần", s["rev7"], s["base_week"], None, s["week_target"]],
            ["  Số bill / tuần", s["bills7"], s["bills28"] / 4, None, s["bills_tgt"]],
            ["  ATV (giá trị bill)", s["atv7"], s["atv4"], b["atv"], s["atv_tgt"]],
            ["    UPT (SP/bill)", s["upt7"], s["upt4"], b["upt"], s["upt_tgt"]],
            ["    Giá TB/SP", s["rev7"] / s["units7"] if s["units7"] else 0, s["asp4"], b["asp"], s["asp_tgt"]]]
    for x in rows:
        x.append(x[4] / x[2] - 1 if x[2] else 0)
    r, f = xl.table(ws, r, ["Driver tree", "7 ngày qua", "TB 4 tuần", "Trung vị chuỗi", "Mục tiêu tuần", "Thay đổi cần"], rows)
    for i, x in enumerate([xl.MONEY, xl.INT, xl.MONEY, xl.DEC2, xl.MONEY]):
        for c in "BCDE":
            ws[f"{c}{f + i}"].number_format = x
        ws[f"F{f + i}"].number_format = "+0%;-0%"
    if s["gap"]:
        ws.cell(r - 1, 1, "Phân rã gap (tr): " + " · ".join(f"{k} {v / 1e6:+,.1f}" for k, v in s["gap"].items())).font = xl.F_NOTE
        r += 1
    ws.cell(r, 1, "Bảng điểm ngày – nhập cuối ngày (ô vàng)").font = xl.F_B
    r = xl.daily_scoreboard(ws, r + 1, s)
    ws.cell(r, 1, "Lead measures & checklist (S1, S2, S4)").font = xl.F_B
    r = xl.action_table(ws, r + 1, [a for a in acts if a["s"] != "S3"])

    # ③ Hàng hóa
    r = xl.section(ws, r, "③ THỰC THI HÀNG HÓA – OTB + PDCA (S3)", 10)
    cat, units_plan = _otb(s)
    ws.cell(r, 1, f"P – Kế hoạch: cần bán ~{units_plan:,.0f} SP tuần này · tồn {s['onhand']:,.0f} SP · "
                  f"cover {s['store_cover']:,.0f} ngày · ST% 28N {_st(s):.0%}").font = xl.F_B
    r += 1
    rows = [[k, x.q28, x.onhand, x.incoming, x.cover if x.cover < 9999 else None, x.st, x.plan_units, x.otb, x.excess,
             "BỔ SUNG" if x.otb > 0 and x.cover < C.LOW_COVER_DAYS * 2 else ("XẢ / LUÂN CHUYỂN NGUYÊN MẪU" if x.excess > 0 else "OK")]
            for k, x in cat.iterrows()]
    r, _ = xl.table(ws, r, ["Nhóm hàng", "Bán 28N", "Tồn", "Đang về", "Cover (ngày)", "ST% 28N",
                            "KH bán tuần (SL)", "OTB cần nhập (SL)", "Tồn dư (SL)", "Hành động"], rows,
                    [None, xl.INT, xl.INT, xl.INT, "0", xl.PCT, xl.INT, xl.INT, xl.INT, None])
    ws.cell(r, 1, "D – Checklist hàng hóa (S3)").font = xl.F_B
    r = xl.action_table(ws, r + 1, [a for a in acts if a["s"] == "S3"])
    ws.cell(r, 1, "D – Bổ sung SKU bán chạy sắp hết").font = xl.F_B
    r = xl.sku_table(ws, r + 1, s["rep"], "rep")
    ws.cell(r, 1, "D – Mẫu top chuỗi CH chưa có").font = xl.F_B
    r = xl.sku_table(ws, r + 1, s["miss"], "miss")
    ws.cell(r, 1, f"D – Cơ hội nhóm hàng so với {p['peer_scope']} (tỷ trọng SL 90N, xu hướng khu vực 28N)").font = xl.F_B
    r, _ = xl.table(ws, r + 1, ["Nhóm hàng", "Tỷ trọng CH", "Tỷ trọng khu vực", "Chênh lệch", "Xu hướng khu vực", "Nhận định"],
                    [[c["cat"], c["store_share"], c["peer_share"], c["gap"], c["growth"], c["hint"]] for c in s["cat_opps"]],
                    [None, xl.PCT, xl.PCT, "+0%;-0%", "+0%;-0%", None])
    ws.cell(r, 1, "D – Đề xuất nhận mẫu ĐỦ SIZE (bán tốt ở CH cùng khu vực, CH không có/chỉ còn size lẻ)").font = xl.F_B
    rq = s["style_requests"]
    r, f2 = xl.table(ws, r + 1, ["Mẫu – màu", "Nhóm", "Bán 28N ở khu vực", "Số CH khu vực bán", "Tình trạng tại CH",
                                 "Size nên nhận (bán chạy của mẫu ở khu vực)", "Kho tổng: số size", "Kho tổng: SL", "Trạng thái"],
                     [[x["style"], x["cat"], x["peer_q28"], x["peer_stores"], x["state"], x["sizes"],
                       x["wh_sizes"], x["wh_units"], None] for x in rq],
                     [None, None, xl.INT, xl.INT, None, None, xl.INT, xl.INT, None])
    if rq:
        xl.status_col(ws, "I", f2, f2 + len(rq) - 1)
    ws.cell(r, 1, f"D – Size lẻ: {s['broken_n']} mẫu / {s['broken_units']:,.0f} SP (còn < {C.MIN_SIZES_FULL_RUN} size, "
                  "không bán 60N) → gom khu xả size lẻ / KM tại chỗ / trả kho – KHÔNG chuyển lẻ sang CH khác").font = xl.F_B
    br = s["broken"]
    r, f3 = xl.table(ws, r + 1, ["Mẫu – màu", "Nhóm", "Size còn", "SL", "Phương án", "Trạng thái"],
                     [[x.style, x.categoryName, x.sizes, x.units, None, None] for x in br.itertuples()],
                     [None, None, None, xl.INT, None, None])
    if len(br):
        from openpyxl.worksheet.datavalidation import DataValidation
        dv = DataValidation(type="list", formula1='"Khu xả size lẻ,KM tại chỗ,Trả kho tổng,Giữ lại"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"E{f3}:E{f3 + len(br) - 1}")
        xl.input_cells(ws, f"E{f3}:E{f3 + len(br) - 1}")
        xl.status_col(ws, "F", f3, f3 + len(br) - 1)
    if s["rotations"]:
        ws.cell(r, 1, "D – Gợi ý luân chuyển NGUYÊN MẪU (đủ size) về khu vực đang bán tốt – GS quyết định").font = xl.F_B
        r, _ = xl.table(ws, r + 1, ["Mẫu – màu", "Nhóm", "Số size", "SL", "Khu vực bán tốt", "Bán 28N ở đó", "Xu hướng nhóm ở đó"],
                        [[x["style"], x["cat"], x["n_sizes"], x["units"], x["to_region"], x["to_q28"], x["to_growth"]] for x in s["rotations"]],
                        [None, None, xl.INT, xl.INT, None, xl.INT, "+0%;-0%"])
    r = _events(ws, r, ctx)
    ws.cell(r, 1, f"D – Tồn chậm: {s['slow_n']} SKU / {s['slow_units']:,.0f} SP (top theo tồn)").font = xl.F_B
    r = xl.sku_table(ws, r + 1, s["slow"], "slow")
    ws.cell(r, 1, "C – Kiểm tra hàng hóa trong tuần").font = xl.F_B
    chk = [("Kiểm đếm hàng bán chạy, đối chiếu tồn hệ thống", "T2"),
           ("Gửi đề xuất bổ sung/OTB cho GS & kho tổng", "T2"),
           ("Đổi layout: tồn chậm ra kệ đầu/khu KM", "T3"),
           ("Nhận hàng, lên kệ trong 24h", "T4"),
           ("Đủ size cho mẫu top 10 của CH", "T5"),
           ("Đếm lại sell-through nhóm hàng chính", "CN")]
    r, f3 = xl.table(ws, r + 1, ["#", "Việc", "Thời điểm", "Trạng thái", "Ghi chú"],
                     [[i + 1, a, d, None, None] for i, (a, d) in enumerate(chk)])
    xl.status_col(ws, "D", f3, f3 + len(chk) - 1)
    xl.input_cells(ws, f"E{f3}:E{f3 + len(chk) - 1}")

    # ④ Đánh giá
    r = xl.section(ws, r, "④ ĐÁNH GIÁ TUẦN (Check – Act) – mang vào họp WIG tuần sau", 10)
    r, f4 = xl.table(ws, r, ["Chiến lược", "Đạt mục tiêu? (Có/Không)", "Điều gì hiệu quả", "Điều gì chưa hiệu quả",
                             "Điều chỉnh tuần sau", "Phụ trách"],
                     [[S_NAME[k], None, None, None, None, None] for k in ("S1", "S2", "S3", "S4")])
    xl.input_cells(ws, f"B{f4}:F{f4 + 3}")
    xl.widths(ws, [30, 42, 14, 14, 16, 22, 12, 12, 14, 22])


def render(ctx, gs, stores, path):
    wb = xl.new_wb()
    _guide(wb, ctx, gs)
    _ogsm_region(wb, ctx, gs, stores)
    _sales_region(wb, ctx, stores)
    _merch_region(wb, ctx, stores)
    for s in sorted(stores, key=lambda x: x["name"]):
        _store(wb, ctx, s)
    wb.active = 1
    wb.save(path)
