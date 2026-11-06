"""Phân tích chuyên sâu cho gợi ý hàng hóa: địa lý/khu vực, đặc tính khách, xu hướng mùa, sự kiện, mẫu đủ size.

Nguyên tắc: KHÔNG chuyển lẻ size giữa cửa hàng. Mọi gợi ý hàng hóa ở cấp MẪU-MÀU (đủ dải size),
dựa trên cửa hàng cùng khu vực (peer) và xu hướng khu vực; giám sát là người quyết định.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

import pandas as pd

import config as C

WOMEN_HINT = ("nữ", "high heels", "flats", "mules", "giày sandal nữ")
SIZE_RE = re.compile(r"^\d{2}(\.5)?$")


def region_of(name: str) -> str:
    parts = str(name).split()
    return parts[1] if len(parts) > 1 and parts[1] in C.REGIONS else "KHÁC"


def climate_note(region: str, month: int) -> str:
    for months, note in C.CLIMATE.get(region, {}).items():
        if month in months:
            return note
    return ""


def split_style(full_name: str):
    """'Giày mọi ... 817 - Black / 43' -> ('Giày mọi ... 817 - Black', '43')."""
    s = str(full_name or "")
    if " / " in s:
        head, tail = s.rsplit(" / ", 1)
        tail = tail.strip()
        if SIZE_RE.match(tail):
            return head.strip(), tail
    return s.strip(), None


# ---------------------------------------------------------------- sự kiện
def _black_friday(y):
    d = date(y, 11, 30)
    while d.weekday() != 4:
        d -= timedelta(days=1)
    return d


def event_dates(start: date, end: date):
    out = []
    for key, name, hint in C.EVENTS:
        for y in range(start.year, end.year + 1):
            if key == "BLACKFRIDAY":
                d = _black_friday(y)
            elif len(key) == 10:
                d = date.fromisoformat(key)
                if d.year != y:
                    continue
            else:
                m, dd = map(int, key.split("-"))
                d = date(y, m, dd)
            if start <= d <= end:
                out.append((d, name, hint))
    return sorted(set(out))


def event_uplift(chain_daily: pd.Series, d: date):
    """Chỉ số doanh số ngày sự kiện (±1 ngày) so với TB cùng thứ 4 tuần trước. None nếu không đủ dữ liệu."""
    win = [d - timedelta(1), d, d + timedelta(1)]
    act, base = [], []
    for x in win:
        if x not in chain_daily.index:
            return None
        ref = [x - timedelta(7 * k) for k in range(1, 5)]
        ref = [chain_daily[r] for r in ref if r in chain_daily.index]
        if len(ref) < 3:
            return None
        act.append(chain_daily[x])
        base.append(sum(ref) / len(ref))
    return sum(act) / sum(base) if sum(base) else None


def events_table(ctx, chain_daily):
    hist_start = min(chain_daily.index) if len(chain_daily) else ctx.as_of
    past = {}
    for d, name, _ in event_dates(hist_start, ctx.as_of - timedelta(1)):
        u = event_uplift(chain_daily, d)
        if u:
            past.setdefault(name, []).append((d, u))
    rows = []
    for d, name, hint in event_dates(ctx.week_start, ctx.week_start + timedelta(C.EVENT_LOOKAHEAD_DAYS)):
        h = past.get(name, [])
        rows.append(dict(date=d, name=name, hint=hint,
                         uplift=h[-1][1] if h else None,
                         ref=f"{h[-1][0]:%d/%m/%Y}" if h else "chưa có lịch sử POS"))
    hist = [dict(date=d, name=n, uplift=u) for n, lst in past.items() for d, u in lst]
    return rows, sorted(hist, key=lambda x: x["date"])


# ---------------------------------------------------------------- dữ liệu cấp mẫu
def enrich(vs, inv, vm):
    names = vm.drop_duplicates("variant_id").set_index("variant_id")[["fullName", "categoryName"]]
    v = vs.join(names, on="variant_id")
    v["fullName"] = v["fullName"].fillna(v["ten"])
    v["categoryName"] = v["categoryName"].fillna("Không rõ")
    v[["style", "size"]] = v["fullName"].apply(lambda s: pd.Series(split_style(s)))
    i = inv.copy()
    i[["style", "size"]] = i["fullName"].apply(lambda s: pd.Series(split_style(s)))
    return v, i


def build(ctx, vs, inv, vm, kpi, combo):
    v, i = enrich(vs, inv, vm)
    stores = ctx.stores
    loc_region = {s["loc"]: region_of(s["name"]) for s in stores}
    store_locs = set(loc_region)
    for s in stores:
        s["region"] = loc_region[s["loc"]]
    by_region = {}
    for s in stores:
        by_region.setdefault(s["region"], []).append(s["loc"])

    # chuỗi theo ngày (sự kiện)
    chain_daily = kpi[kpi["MaLocation"].isin(store_locs)].groupby("d")["rev"].sum()
    ev_rows, ev_hist = events_table(ctx, chain_daily)
    ctx.events, ctx.event_hist = ev_rows, ev_hist

    # xu hướng nhóm hàng theo khu vực: 28N gần nhất vs 28N trước (dùng q28 và q60-q28 xấp xỉ 32N trước)
    v_st = v[v["MaLocation"].isin(store_locs)].copy()
    v_st["region"] = v_st["MaLocation"].map(loc_region)
    v_st["q_prev"] = (v_st["q60"] - v_st["q28"]) * 28 / 32
    reg_cat = v_st.groupby(["region", "categoryName"])[["q28", "q_prev", "q90"]].sum()
    reg_tot = v_st.groupby("region")[["q28", "q_prev", "q90"]].sum()
    ctx.region_trend = {}
    for reg in reg_tot.index:
        rc = reg_cat.loc[reg].copy()
        rc["share"] = rc["q28"] / (reg_tot.loc[reg, "q28"] or 1)
        rc["growth"] = rc.apply(lambda x: (x.q28 / x.q_prev - 1) if x.q_prev >= 3 else None, axis=1)
        ctx.region_trend[reg] = rc.sort_values("q28", ascending=False)

    # kho tổng: số size còn hàng theo mẫu
    wh = i[i["locName"].isin(C.WAREHOUSES) & (i["qty_available"] > 0)]
    wh_style = wh.groupby("style").agg(wh_sizes=("size", "nunique"), wh_units=("qty_available", "sum"))

    combo = combo.copy()
    ch = {}
    for loc, g in combo.groupby("MaLocation"):
        d = {int(r.combo): r for r in g.itertuples()}
        if 1 in d and 0 in d and d[1].bills >= 5 and d[0].bills:
            ch[loc] = (d[1].units / d[1].bills, d[0].units / d[0].bills, d[1].bills / (d[1].bills + d[0].bills))

    chain_asp = ctx.bench["asp"] or 1
    for s in stores:
        loc, reg = s["loc"], s["region"]
        peers = [l for l in by_region.get(reg, []) if l != loc]
        peer_scope = f"CH cùng khu vực {C.REGIONS.get(reg, reg)} ({len(peers)} CH)"
        if len(peers) < C.PEER_MIN_STORES:
            peers = [l for l in store_locs if l != loc]
            peer_scope = f"toàn chuỗi ({len(peers)} CH)"
        sv = v[v["MaLocation"] == loc]
        pv = v[v["MaLocation"].isin(peers)]

        # --- Hồ sơ cửa hàng
        cat90 = sv.groupby("categoryName")["q90"].sum()
        tot90 = cat90.sum() or 1
        women = cat90[[c for c in cat90.index if any(h in str(c).lower() for h in WOMEN_HINT)]].sum() / tot90
        sizes = sv[sv["size"].notna()].groupby("size")["q90"].sum().sort_values(ascending=False)
        core_sizes = list(sizes.head(4).index)
        size_curve = (sizes / sizes.sum()).round(2) if sizes.sum() else sizes
        s["profile"] = dict(
            region=C.REGIONS.get(reg, reg), climate=climate_note(reg, ctx.week_start.month),
            archetype=f"{s['doitac']} · {s['loai']}",
            price_tier=s["asp4"] / chain_asp if s["asp4"] else None,
            women_share=women, addon_share=s["addon_share"],
            core_sizes=", ".join(core_sizes) if core_sizes else "-",
            size_curve=size_curve, combo=ch.get(loc), peer_scope=peer_scope,
        )

        # --- Cơ hội nhóm hàng: tỷ trọng CH vs peer + xu hướng khu vực
        pc = pv.groupby("categoryName")["q90"].sum()
        pshare = pc / (pc.sum() or 1)
        sshare = cat90 / tot90
        trend = ctx.region_trend.get(reg)
        cats = []
        for c in pshare.index.union(sshare.index):
            ps, ss_ = float(pshare.get(c, 0)), float(sshare.get(c, 0))
            if (ps < 0.02 and ss_ < 0.02) or c in ("Khác", "Không rõ"):
                continue
            g = trend.loc[c, "growth"] if trend is not None and c in trend.index else None
            gap = ss_ - ps
            if gap <= -0.03 or (gap < -0.01 and g is not None and g >= 0.2):
                hint = "THIẾU so với khu vực – tăng trưng bày, đề xuất nhận mẫu bán chạy của nhóm"
            elif gap >= 0.05:
                hint = "MẠNH hơn khu vực – giữ đủ hàng, làm điểm nhấn"
            else:
                hint = "Tương đương khu vực"
            if g is not None and g >= 0.2:
                hint += " · nhóm đang TĂNG trong khu vực"
            elif g is not None and g <= -0.2:
                hint += " · nhóm đang GIẢM trong khu vực"
            cats.append(dict(cat=c, store_share=ss_, peer_share=ps, gap=gap, growth=g, hint=hint))
        s["cat_opps"] = sorted(cats, key=lambda x: x["gap"])

        # --- Mẫu bán tốt ở peer mà CH thiếu / chỉ còn size lẻ -> đề xuất nhận ĐỦ SIZE
        si = i[i["loc_id"] == loc]
        st_stock = si[si["qty_onhand"] > 0]
        st_sizes = st_stock.groupby("style")["size"].nunique()
        st_units = st_stock.groupby("style")["qty_onhand"].sum()
        pst = (pv.groupby(["style", "categoryName"])
               .agg(q28=("q28", "sum"), r28=("r28", "sum"), n_store=("MaLocation", "nunique"),
                    sized=("size", lambda x: x.notna().any())).reset_index())
        pst = pst[(pst["n_store"] >= 2) & (pst["q28"] >= 4) & (pst["r28"] / pst["q28"] >= C.MIN_ITEM_PRICE)]
        pst = pst.sort_values("q28", ascending=False)
        psz = pv[pv["size"].notna()].groupby(["style", "size"])["q90"].sum()

        def style_sizes(style):
            if style not in psz.index.get_level_values(0):
                return "—"
            z = psz.loc[style]
            z = z[z > 0].sort_values(ascending=False)
            top = sorted(z.head(5).index, key=lambda t: float(t))
            return ", ".join(top) if top else "—"

        req = []
        for x in pst.itertuples():
            if x.sized:
                have = int(st_sizes.get(x.style, 0))
                if have >= C.MIN_SIZES_FULL_RUN:
                    continue
                state = "Không có" if have == 0 else f"Chỉ còn {have} size"
            else:
                if st_units.get(x.style, 0) > 0:
                    continue
                state = "Không có"
            w = wh_style.loc[x.style] if x.style in wh_style.index else None
            req.append(dict(style=x.style, cat=x.categoryName, peer_q28=x.q28, peer_stores=x.n_store,
                            state=state, wh_sizes=int(w.wh_sizes) if w is not None and x.sized else None,
                            wh_units=int(w.wh_units) if w is not None else 0,
                            sizes=style_sizes(x.style) if x.sized else "—"))
            if len(req) >= C.TOP_N_LIST:
                break
        s["style_requests"] = req

        # --- Size lẻ: mẫu còn < N size, không bán 60 ngày tại CH -> gom/xả, KHÔNG chuyển lẻ
        stock = si[si["qty_onhand"] > 0]
        sold60 = sv.groupby("style")["q60"].sum()
        g = stock.groupby(["style", "categoryName"]).agg(sizes=("size", lambda x: ", ".join(sorted(x.dropna().unique()))),
                                                         n_sizes=("size", "nunique"), units=("qty_onhand", "sum")).reset_index()
        g = g[g["n_sizes"].between(1, C.MIN_SIZES_FULL_RUN - 1)]
        g["sold60"] = g["style"].map(sold60).fillna(0)
        broken = g[g["sold60"] == 0].sort_values("units", ascending=False)
        s["broken_n"], s["broken_units"] = len(broken), float(broken["units"].sum())
        s["broken"] = broken.head(C.TOP_N_LIST)

        # --- Mẫu nguyên dải size đứng hàng tại CH nhưng bán tốt ở khu vực khác -> gợi ý luân chuyển NGUYÊN MẪU
        full = g_full = stock.groupby(["style", "categoryName"]).agg(n_sizes=("size", "nunique"), units=("qty_onhand", "sum")).reset_index()
        full = full[(full["n_sizes"] >= C.MIN_SIZES_FULL_RUN)]
        full = full[full["style"].map(sold60).fillna(0) == 0]
        other = v_st[(v_st["region"] != reg)].groupby(["style", "region"])["q28"].sum()
        rot = []
        for x in full.sort_values("units", ascending=False).itertuples():
            if x.style not in other.index.get_level_values(0):
                continue
            best = other.loc[x.style].sort_values(ascending=False)
            to = best.index[0]
            if best.iloc[0] < 5:
                continue
            tt = ctx.region_trend.get(to)
            g = tt.loc[x.categoryName, "growth"] if tt is not None and x.categoryName in tt.index else None
            if g is not None and g < -0.15:
                continue
            rot.append(dict(style=x.style, cat=x.categoryName, n_sizes=x.n_sizes, units=x.units,
                            to_region=C.REGIONS.get(to, to), to_q28=float(best.iloc[0]), to_growth=g))
            if len(rot) >= 10:
                break
        s["rotations"] = rot
