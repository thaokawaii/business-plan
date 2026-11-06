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
    # 3. UPT
    if s["upt4"] < b["upt"] * C.BENCH_GAP or s["upt_tgt"] > s["upt4"] * 1.02:
        add("UPT (SP/bill)", f"Bán kèm: nâng UPT {s['upt4']:.2f} → {s['upt_tgt']:.2f} (trung vị chuỗi {b['upt']:.2f}). "
            f"Mỗi bill giày gợi ý vớ/lót giày/thắt lưng/ví; tỷ trọng phụ kiện hiện {s['addon_share']:.0%}.",
            "UPT", round(s["upt_tgt"], 2))
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
    if s["slow_n"]:
        add("Hàng hóa", f"Đẩy hàng tồn chậm: {s['slow_n']} SKU / {s['slow_units']:,.0f} SP không bán {C.SLOW_MOVER_DAYS} ngày – "
            "đưa ra kệ đầu/khu khuyến mãi, thi đua nhân viên, đề xuất điều chuyển.",
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
    A.append(dict(nhom="Hàng hóa", viec="Duyệt đề xuất bổ sung & điều chuyển giữa các CH trong vùng (sheet Điều chuyển).",
                  kpi="Phiếu điều chuyển", chi_tieu=1, owner="GS", han=ctx.week_start + timedelta(days=1)))
    A.append(dict(nhom="Vận hành", viec="Tổng hợp bảng điểm các CH cuối tuần, so sánh lead measures (bill, UPT).",
                  kpi="Báo cáo tuần", chi_tieu=1, owner="GS", han=ctx.week_end))
    return A
