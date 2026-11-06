"""Engine tính toán dùng chung cho cả 3 mô hình."""
from __future__ import annotations
import calendar
import math
from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

import config as C
from . import data

WD = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


def month_days(y, m):
    return [date(y, m, d) for d in range(1, calendar.monthrange(y, m)[1] + 1)]


def safe_div(a, b):
    return a / b if b else 0.0


def _non_merch(code, name):
    """True với công cụ dụng cụ / vật tư / bao bì (không phải hàng bán)."""
    c = code.fillna("").astype(str).str.upper()
    n = name.fillna("").astype(str).str.lower()
    m = c.str.startswith(tuple(p.upper() for p in C.NON_MERCH_SKU_PREFIXES))
    for k in C.NON_MERCH_NAME_KEYWORDS:
        m |= n.str.contains(k.lower(), regex=False)
    return m


@dataclass
class Ctx:
    as_of: date
    week_start: date
    week_end: date
    week_label: str
    weights: dict
    stores: list = field(default_factory=list)       # list[dict]
    bench: dict = field(default_factory=dict)
    inv_snapshot: date = None


def build(week_start: date | None = None, allow_gaps: bool = False) -> Ctx:
    as_of = data.last_full_day()
    miss = data.missing_days(as_of)
    if miss and not allow_gaps:
        raise SystemExit(f"Dữ liệu bán hàng thiếu {len(miss)} ngày ({min(miss)} → {max(miss)}). "
                         "Có thể ETL đang nạp lại – chạy lại sau, hoặc thêm --allow-gaps nếu chấp nhận.")
    if week_start is None:   # mặc định: tuần kế tiếp sau ngày dữ liệu
        week_start = as_of + timedelta(days=7 - as_of.weekday())
    week_end = week_start + timedelta(days=6)
    iso = week_start.isocalendar()
    label = f"{iso[0]}-W{iso[1]:02d}"

    months = sorted({(as_of.year, as_of.month)} | {(d.year, d.month) for d in
                     (week_start + timedelta(i) for i in range(7))})
    tg = data.targets(months)
    start = min(date(as_of.year, as_of.month, 1), as_of - timedelta(days=89))
    kpi = data.daily_kpi(start, as_of)
    kpi["d"] = pd.to_datetime(kpi["d"]).dt.date

    # Trọng số theo thứ trong tuần (8 tuần gần nhất, các CH có target)
    locs = set(tg["MaLocation"])
    k8 = kpi[(kpi["MaLocation"].isin(locs)) & (kpi["d"] > as_of - timedelta(days=56))]
    by_wd = k8.groupby(k8["d"].map(lambda d: d.weekday()))["rev"].sum()
    mean = by_wd.mean() if len(by_wd) else 1
    weights = {i: float(by_wd.get(i, mean) / mean) for i in range(7)}

    ctx = Ctx(as_of, week_start, week_end, label, weights)

    vs = data.variant_sales(as_of)
    inv = data.inventory()
    ctx.inv_snapshot = inv["snapshotDate"].max() if len(inv) else None
    vm = data.variant_master()
    inv = inv[~_non_merch(inv["productCode"], inv["fullName"])]
    vs = vs[~_non_merch(vs["sku"], vs["ten"])]
    dorm = data.dormant_customers(as_of).set_index("MaLocation")["n"].to_dict()

    cat_map = vm.drop_duplicates("variant_id").set_index("variant_id")["categoryName"].to_dict()
    vs["category"] = vs["variant_id"].map(cat_map).fillna("Không rõ")

    # Kho tổng (nguồn bổ sung)
    wh = inv[inv["locName"].isin(C.WAREHOUSES)].groupby("variant_id")["qty_available"].sum().clip(lower=0)

    d28 = as_of - timedelta(days=27)
    d7 = as_of - timedelta(days=6)

    # ---- Benchmark chuỗi (28 ngày) ----
    base = kpi[kpi["d"] >= d28].groupby("MaLocation")[["rev", "bills", "units"]].sum()
    base = base[base.index.isin(locs) & (base["bills"] > 0)]
    base["atv"] = base["rev"] / base["bills"]
    base["upt"] = base["units"] / base["bills"]
    base["asp"] = base["rev"] / base["units"]
    ctx.bench = {k: float(base[k].median()) for k in ("atv", "upt", "asp")} if len(base) else {"atv": 0, "upt": 0, "asp": 0}

    # Top mẫu bán chạy toàn chuỗi (product_id, 28 ngày, tại CH)
    vs_st = vs[vs["MaLocation"].isin(locs)]
    top_products = (vs_st.groupby("product_id").agg(q28=("q28", "sum"), ten=("ten", "first"))
                    .sort_values("q28", ascending=False).head(30))

    cur_month = (as_of.year, as_of.month)
    tg_cur = tg[(tg["Nam"] == as_of.year) & (tg["Thang"] == as_of.month)]
    # danh sách CH: ưu tiên target tháng của tuần kế hoạch
    wk_month = (week_start.year, week_start.month)
    tg_wk = tg[(tg["Nam"] == wk_month[0]) & (tg["Thang"] == wk_month[1])]
    roster = (tg_wk if len(tg_wk) else tg_cur).drop_duplicates("MaLocation")

    tmap = {(r.MaLocation, r.Nam, r.Thang): float(r.Target or 0) for r in tg.itertuples()}

    for r in roster.itertuples():
        loc = r.MaLocation
        k = kpi[kpi["MaLocation"] == loc]
        daily = k.set_index("d")["rev"].to_dict()

        def mtd(y, m):
            return float(sum(v for d, v in daily.items() if d.year == y and d.month == m and d <= as_of))

        # Target theo ngày cho tuần kế hoạch (phân bổ phần còn thiếu theo trọng số thứ)
        day_rows = []
        for i in range(7):
            d = week_start + timedelta(i)
            T = tmap.get((loc, d.year, d.month), 0.0)
            if (d.year, d.month) == cur_month:
                done = mtd(*cur_month)
                rem = [x for x in month_days(d.year, d.month) if x > as_of]
            else:
                done = 0.0
                rem = month_days(d.year, d.month)
            wsum = sum(weights[x.weekday()] for x in rem) or 1
            dt = max(0.0, (T - done)) * weights[d.weekday()] / wsum
            day_rows.append({"date": d, "wd": WD[d.weekday()], "target": dt})
        week_target = sum(x["target"] for x in day_rows)

        T_cur = tmap.get((loc, *cur_month), 0.0)
        mtd_cur = mtd(*cur_month)
        dim = calendar.monthrange(*cur_month)[1]
        days_left = dim - as_of.day
        k7 = k[k["d"] >= d7]
        k28 = k[k["d"] >= d28]
        rev7, bills7, units7 = (float(k7[c].sum()) for c in ("rev", "bills", "units"))
        rev28, bills28, units28 = (float(k28[c].sum()) for c in ("rev", "bills", "units"))
        rev_pos28 = float(k28["rev_pos"].sum())
        # dự báo theo nhịp TB 28 ngày, có trọng số thứ trong tuần
        rem_cur = [x for x in month_days(*cur_month) if x > as_of]
        forecast = mtd_cur + rev28 / 28 * sum(weights[x.weekday()] for x in rem_cur)
        need_per_day = max(0.0, T_cur - mtd_cur) / days_left if days_left > 0 else 0.0

        atv4, upt4, asp4 = safe_div(rev28, bills28), safe_div(units28, bills28), safe_div(rev28, units28)
        base_week = rev28 / 4
        ach_fc = safe_div(forecast, T_cur)
        rag = "XANH" if ach_fc >= C.RAG_GREEN else ("VÀNG" if ach_fc >= C.RAG_AMBER else "ĐỎ")

        # ---- Driver tree: mục tiêu tuần ----
        uplift = safe_div(week_target, base_week) - 1 if base_week else 0
        b = ctx.bench
        upt_tgt = max(upt4 * 1.03, min(b["upt"], upt4 * 1.15)) if upt4 else b["upt"]
        asp_tgt = max(asp4 * 1.02, min(b["asp"], asp4 * 1.05)) if asp4 else b["asp"]
        atv_tgt = upt_tgt * asp_tgt
        bills_tgt = math.ceil(safe_div(week_target, atv_tgt)) if atv_tgt else 0
        # Phân rã gap (log) giữa nền 4 tuần và mục tiêu tuần
        gap = {}
        if base_week and week_target and bills28 and atv_tgt:
            tot = math.log(week_target / base_week)
            parts = {"Số bill": math.log(bills_tgt / (bills28 / 4)) if bills_tgt else 0,
                     "UPT": math.log(upt_tgt / upt4) if upt4 else 0,
                     "Giá TB/SP": math.log(asp_tgt / asp4) if asp4 else 0}
            s = sum(parts.values()) or 1
            gap = {kk: (week_target - base_week) * v / s for kk, v in parts.items()} if tot else {}

        # ---- Tồn kho cửa hàng ----
        inv_s = inv[inv["loc_id"] == loc][["variant_id", "product_id", "productCode", "fullName",
                                           "categoryName", "qty_onhand", "qty_available", "qty_incoming"]]
        sal_s = vs[vs["MaLocation"] == loc][["variant_id", "product_id", "sku", "ten", "category",
                                             "q28", "q60", "q90", "r28", "last_sold"]]
        m = inv_s.merge(sal_s, on="variant_id", how="outer", suffixes=("", "_s"))
        m["product_id"] = m["product_id"].fillna(m["product_id_s"])
        m["productCode"] = m["productCode"].fillna(m["sku"])
        m["fullName"] = m["fullName"].fillna(m["ten"])
        m["categoryName"] = m["categoryName"].fillna(m["category"]).fillna("Không rõ")
        for c in ("qty_onhand", "qty_available", "qty_incoming", "q28", "q60", "q90", "r28"):
            m[c] = m[c].fillna(0).astype(float)
        m["rate"] = m["q28"] / 28
        m["cover"] = m.apply(lambda x: x.qty_onhand / x.rate if x.rate > 0 else (9999 if x.qty_onhand > 0 else 0), axis=1)
        m["wh_avail"] = m["variant_id"].map(wh).fillna(0)

        rep = m[(m["q28"] >= 2) & (m["cover"] < C.LOW_COVER_DAYS)].copy()
        rep["de_xuat"] = (rep["rate"] * C.TARGET_COVER_DAYS - rep["qty_onhand"] - rep["qty_incoming"]).clip(lower=0).apply(math.ceil)
        rep = rep[rep["de_xuat"] > 0].sort_values("q28", ascending=False).head(C.TOP_N_LIST)

        slow = m[(m["qty_onhand"] > 0) & (m["q60"] == 0)].sort_values("qty_onhand", ascending=False)
        slow_units = float(slow["qty_onhand"].sum())
        over = m[(m["qty_onhand"] >= 3) & (m["q28"] > 0) & (m["cover"] > C.OVERSTOCK_COVER_DAYS)]

        have = set(m.loc[m["qty_onhand"] > 0, "product_id"].dropna().astype("int64"))
        miss = top_products[~top_products.index.isin(have)].head(10)

        cat = m.groupby("categoryName").agg(q28=("q28", "sum"), r28=("r28", "sum"),
                                            onhand=("qty_onhand", "sum"), incoming=("qty_incoming", "sum"))
        cat["cover"] = cat.apply(lambda x: x.onhand / (x.q28 / 28) if x.q28 else (9999 if x.onhand else 0), axis=1)
        cat["st"] = cat.apply(lambda x: safe_div(x.q28, x.q28 + x.onhand), axis=1)
        cat["otb_units"] = (cat["q28"] / 28 * (7 + C.TARGET_COVER_DAYS) - cat["onhand"] - cat["incoming"]).clip(lower=0).round()
        cat = cat[(cat["q28"] > 0) | (cat["onhand"] > 0)].sort_values("r28", ascending=False)

        addon = cat[cat.index.isin(C.ADDON_CATEGORIES)]
        addon_share = safe_div(float(addon["q28"].sum()), units28)

        ctx.stores.append(dict(
            loc=loc, name=r.TenCuaHang, gs=r.TenGiamSat, loai=r.Loai, doitac=r.DoiTac,
            target_month=T_cur, mtd=mtd_cur, ach_mtd=safe_div(mtd_cur, T_cur), forecast=forecast,
            ach_fc=ach_fc, rag=rag, days_left=days_left, need_per_day=need_per_day, avg7=rev7 / 7,
            week_target=week_target, days=day_rows, base_week=base_week, uplift=uplift,
            rev7=rev7, bills7=bills7, units7=units7, rev28=rev28, bills28=bills28, units28=units28,
            pos_share=safe_div(rev_pos28, rev28),
            atv4=atv4, upt4=upt4, asp4=asp4, atv7=safe_div(rev7, bills7), upt7=safe_div(units7, bills7),
            upt_tgt=upt_tgt, asp_tgt=asp_tgt, atv_tgt=atv_tgt, bills_tgt=bills_tgt, gap=gap,
            dormant=int(dorm.get(loc, 0)), addon_share=addon_share,
            onhand=float(m["qty_onhand"].sum()), inv_skus=int((m["qty_onhand"] > 0).sum()),
            store_cover=safe_div(float(m["qty_onhand"].sum()), units28 / 28),
            rep=rep, slow=slow.head(C.TOP_N_LIST), slow_n=len(slow), slow_units=slow_units,
            over=over, miss=miss, cat=cat, inv_df=m,
        ))
    return ctx


def transfers(stores):
    """Gợi ý điều chuyển giữa các CH cùng giám sát: CH dư (cover > ngưỡng) -> CH thiếu."""
    out = []
    excess = {}
    for s in stores:
        for x in s["inv_df"].itertuples():
            if x.qty_onhand >= 2 and (x.cover > C.OVERSTOCK_COVER_DAYS):
                give = int(x.qty_onhand - math.ceil(x.rate * C.TARGET_COVER_DAYS)) if x.rate else int(x.qty_onhand) - 1
                if give > 0:
                    excess.setdefault(x.variant_id, []).append([s["name"], give])
    for s in stores:
        for x in s["rep"].itertuples():
            need = int(x.de_xuat)
            for src in excess.get(x.variant_id, []):
                if need <= 0:
                    break
                if src[0] == s["name"] or src[1] <= 0:
                    continue
                q = min(need, src[1])
                out.append(dict(tu=src[0], den=s["name"], sku=x.productCode, ten=x.fullName, sl=q))
                src[1] -= q
                need -= q
    return out
