"""Sinh hành động từ chẩn đoán số liệu (dùng chung cho 3 mô hình).
Mỗi action: nhom (đòn bẩy), viec, kpi, chi_tieu, owner, han."""
from datetime import timedelta

import config as C


def tr(v):
    return f"{v / 1e6:,.1f} tr"


def store_actions(s, ctx):
    ws = ctx.week_start
    A = []
    b = ctx.bench

    def add(nhom, viec, kpi, chi_tieu, owner="CHT", han=None):
        A.append(dict(nhom=nhom, viec=viec, kpi=kpi, chi_tieu=chi_tieu, owner=owner,
                      han=han or (ws + timedelta(days=6))))

    # 1. Nhịp doanh số
    if s["week_target"] > 0:
        add("Doanh số", f"Đạt target tuần {tr(s['week_target'])} (TB 4 tuần: {tr(s['base_week'])}/tuần, "
            f"cần {s['uplift']:+.0%}). Theo dõi bảng điểm ngày, chốt số cuối mỗi ca.",
            "Doanh số tuần", s["week_target"])
    # 2. Số bill
    bills_now = s["bills28"] / 4
    if s["bills_tgt"] > bills_now * 1.02:
        add("Số bill (lượt mua)", f"Tăng bill từ {bills_now:.0f} lên {s['bills_tgt']} bill/tuần "
            f"(~{s['bills_tgt'] / 7:.0f}/ngày, ưu tiên T7–CN chiếm {(ctx.weights[5] + ctx.weights[6]) / 7:.0%} doanh số).",
            "Số bill tuần", s["bills_tgt"])
        if s["dormant"]:
            n = min(s["dormant"], 140)
            add("Số bill (lượt mua)", f"CRM: gọi/nhắn Zalo {n} KH cũ không quay lại 60–365 ngày "
                f"(CH có {s['dormant']} KH) – mời xem BST mới/ưu đãi.", "Số KH liên hệ", n)
        add("Số bill (lượt mua)", "Mời khách tại cửa/lối đi TTTM giờ cao điểm (11–13h, 18–21h), "
            "đặt standee ưu đãi; ghi nhận số khách vào cửa (traffic) để tính tỷ lệ chuyển đổi.",
            "Số giờ mời khách / traffic", 14)
    # 2b. Sự kiện trong tuần kế hoạch
    for e in getattr(ctx, "events", []):
        if ws <= e["date"] <= ws + timedelta(days=6):
            up = f" · lần gần nhất DS chuỗi ×{e['uplift']:.2f}" if e["uplift"] else ""
            add("Số bill (lượt mua)", f"Sự kiện {e['name']} ({e['date']:%d/%m}): {e['hint']}. Nhắn KH cũ trước 2 ngày, "
                f"trưng bày & tăng ca nhân sự ngày cao điểm{up}.", "Bill ngày sự kiện",
                round(s["bills_tgt"] / 7 * 1.5), "CHT", e["date"] - timedelta(days=1))
    # 3. UPT
    if s["upt4"] < b["upt"] * C.BENCH_GAP or s["upt_tgt"] > s["upt4"] * 1.02:
        add("UPT (SP/bill)", f"Bán kèm: nâng UPT {s['upt4']:.2f} → {s['upt_tgt']:.2f} (trung vị chuỗi {b['upt']:.2f}). "
            f"Mỗi bill giày gợi ý vớ/lót giày/thắt lưng/ví; tỷ trọng phụ kiện hiện {s['addon_share']:.0%}.",
            "UPT", round(s["upt_tgt"], 2))
    cb = s.get("profile", {}).get("combo")
    if cb and cb[0] > cb[1] * 1.2:
        add("UPT (SP/bill)", f"Đẩy combo/mua nhiều: bill combo có UPT {cb[0]:.1f} vs {cb[1]:.1f} bill thường; "
            f"hiện chỉ {cb[2]:.0%} bill dùng combo → mục tiêu {min(cb[2] + 0.1, 0.5):.0%}.",
            "% bill combo", round(min(cb[2] + 0.1, 0.5), 2))
    # 4. Giá TB
    if s["asp4"] < b["asp"] * C.BENCH_GAP:
        add("Giá TB/SP", f"Upsell: nâng giá TB/SP {tr(s['asp4'])} → {tr(s['asp_tgt'])} (chuỗi {tr(b['asp'])}). "
            "Trưng bày dòng cao cấp ngang tầm mắt, giới thiệu chất liệu/bảo hành.",
            "Giá TB/SP", s["asp_tgt"])
    # 5. Hàng hóa
    if len(s["rep"]):
        add("Hàng hóa", f"Đặt bổ sung {len(s['rep'])} SKU bán chạy sắp hết (cover < {C.LOW_COVER_DAYS} ngày), "
            f"tổng {int(s['rep']['de_xuat'].sum())} SP – xem danh sách bổ sung.", "SKU bán chạy đủ hàng", len(s["rep"]),
            "CHT + GS", ws + timedelta(days=1))
    if len(s["miss"]):
        add("Hàng hóa", f"Đề xuất nhận {len(s['miss'])} mẫu top bán chạy toàn chuỗi mà CH đang không có tồn.",
            "Mẫu top chuỗi có hàng", len(s["miss"]), "GS", ws + timedelta(days=2))
    prof = s.get("profile", {})
    if prof.get("climate"):
        add("Hàng hóa", f"Mùa vụ {prof['region']}: {prof['climate']}. Sắp xếp lại khu trưng bày chính theo mùa.",
            "Layout theo mùa", 1, "CHT", ws + timedelta(days=2))
    for c in [c for c in s.get("cat_opps", []) if c["hint"].startswith("THIẾU")][:2]:
        gr = f", khu vực {c['growth']:+.0%}" if c["growth"] is not None else ""
        add("Hàng hóa", f"Nhóm {c['cat']}: CH {c['store_share']:.0%} vs khu vực {c['peer_share']:.0%}{gr} – "
            "tăng mặt trưng bày, đề xuất nhận mẫu bán chạy của nhóm (đủ size).", "Tỷ trọng nhóm", round(c["peer_share"], 2),
            "CHT + GS", ws + timedelta(days=2))
    if s.get("style_requests"):
        add("Hàng hóa", f"Đề xuất nhận {len(s['style_requests'])} mẫu đang bán tốt ở {prof.get('peer_scope', 'CH cùng khu vực')} "
            f"mà CH không có/chỉ còn size lẻ – nhận ĐỦ DẢI SIZE (size bán chạy của CH: {prof.get('core_sizes', '-')}).",
            "Mẫu nhận đủ size", len(s["style_requests"]), "GS", ws + timedelta(days=2))
    if s.get("broken_n"):
        add("Hàng hóa", f"Size lẻ: {s['broken_n']} mẫu / {s['broken_units']:,.0f} SP chỉ còn < {C.MIN_SIZES_FULL_RUN} size, không bán 60 ngày – "
            "gom vào khu xả size lẻ/KM tại chỗ hoặc trả kho tổng; KHÔNG chuyển lẻ size sang CH khác.",
            "SP size lẻ bán/xử lý", max(1, round(s["broken_units"] * 0.1)))
    if s["slow_n"]:
        add("Hàng hóa", f"Đẩy hàng tồn chậm: {s['slow_n']} SKU / {s['slow_units']:,.0f} SP không bán {C.SLOW_MOVER_DAYS} ngày – "
            "kệ đầu/khu KM, combo, thi đua nhân viên. Mẫu còn đủ size bán tốt ở khu vực khác: xem gợi ý luân chuyển nguyên mẫu.",
            "SP tồn chậm bán được", max(1, round(s["slow_units"] * 0.05)))
    # 6. Nhịp vận hành 4DX
    add("Vận hành", "Họp đầu ca 10 phút: xem bảng điểm hôm qua, cam kết 1 việc/người cho hôm nay.",
        "Số buổi họp", 7)
    add("Vận hành", "GS họp WIG 20 phút với CHT (đầu tuần): xem lead measures, gỡ vướng, chốt cam kết tuần sau.",
        "Buổi WIG", 1, "GS", ws)
    return A


def supervisor_actions(stores, ctx):
    red = [s for s in stores if s["rag"] == "ĐỎ"]
    A = []
    if red:
        A.append(dict(nhom="Ưu tiên", viec="Ghé trực tiếp " + ", ".join(s["name"] for s in red[:4]) +
                      (" …" if len(red) > 4 else "") + " (dự báo < 85% target).",
                      kpi="Số CH đỏ được coaching", chi_tieu=min(len(red), 4), owner="GS", han=ctx.week_end))
    A.append(dict(nhom="Hàng hóa", viec="Duyệt đề xuất nhận mẫu ĐỦ SIZE, gợi ý luân chuyển NGUYÊN MẪU theo khu vực và "
                  "phương án xử lý size lẻ (sheet Hàng hóa vùng). Không chuyển lẻ size giữa CH.",
                  kpi="Đề xuất đã duyệt", chi_tieu=1, owner="GS", han=ctx.week_start + timedelta(days=1)))
    A.append(dict(nhom="Vận hành", viec="Tổng hợp bảng điểm các CH cuối tuần, so sánh lead measures (bill, UPT).",
                  kpi="Báo cáo tuần", chi_tieu=1, owner="GS", han=ctx.week_end))
    return A
