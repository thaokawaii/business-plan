"""Lấy dữ liệu từ SQL Server (chỉ đọc)."""
from datetime import date, timedelta

import config as C
from .db import query


def _order_filter():
    f = ["o.MaLocation IS NOT NULL"]
    if C.EXCLUDE_ORDER_STATUS:
        f.append("ISNULL(o.TTDonHang,'') NOT IN (%s)" % ",".join(f"'{s}'" for s in C.EXCLUDE_ORDER_STATUS))
    if C.EXCLUDE_PAYMENT_STATUS:
        f.append("ISNULL(o.TTThanhToan,'') NOT IN (%s)" % ",".join(f"'{s}'" for s in C.EXCLUDE_PAYMENT_STATUS))
    if C.INCLUDE_CHANNELS:
        f.append("o.Nguon IN (%s)" % ",".join(f"'{s}'" for s in C.INCLUDE_CHANNELS))
    return " AND ".join(f)


def last_full_day():
    df = query("SELECT CAST(MAX(TaoLuc) AS date) d FROM Haravan_DonHang_ChiTiet WHERE Nguon='pos'")
    d = df.iloc[0, 0]
    return d - timedelta(days=1)   # ngày hiện tại chưa đủ -> lấy ngày trước


def missing_days(as_of: date, days: int = 35):
    """Các ngày không có đơn POS nào trong `days` ngày gần nhất (dấu hiệu ETL chưa nạp xong)."""
    df = query("""SELECT DISTINCT CAST(TaoLuc AS date) d FROM Haravan_DonHang_ChiTiet
                  WHERE Nguon='pos' AND TaoLuc >= %s AND TaoLuc < %s""",
               (as_of - timedelta(days=days - 1), as_of + timedelta(days=1)))
    have = set(df["d"]) if len(df) else set()
    return [as_of - timedelta(days=i) for i in range(days) if as_of - timedelta(days=i) not in have]


def targets(months):
    cond = " OR ".join(f"(Nam={y} AND Thang={m})" for y, m in months)
    df = query(f"""SELECT TenCuaHang, MaLocation, TenGiamSat, Loai, DoiTac, LoaiThu, Nam, Thang, Target
                   FROM targetVN WHERE MaLocation IS NOT NULL AND ({cond})""")
    df["TenGiamSat"] = df["TenGiamSat"].fillna("Chưa phân GS").replace({"New": "Chưa phân GS (New)"})
    return df


def daily_kpi(start: date, end: date):
    """Doanh thu / bill / số lượng theo cửa hàng-ngày."""
    return query(f"""
        SELECT o.MaLocation, CAST(o.TaoLuc AS date) d,
               SUM({C.REVENUE_EXPR}) rev, COUNT(DISTINCT o.MaDon) bills, SUM(o.SP_SL) units,
               SUM(CASE WHEN o.Nguon='pos' THEN {C.REVENUE_EXPR} ELSE 0 END) rev_pos
        FROM Haravan_DonHang_ChiTiet o
        WHERE {_order_filter()} AND o.TaoLuc >= %s AND o.TaoLuc < %s
        GROUP BY o.MaLocation, CAST(o.TaoLuc AS date)""", (start, end + timedelta(days=1)))


def variant_sales(as_of: date):
    """Bán theo biến thể tại từng cửa hàng: 28 / 60 / 90 ngày."""
    d28, d60, d90 = (as_of - timedelta(days=n - 1) for n in (28, 60, 90))
    return query(f"""
        SELECT o.MaLocation, o.SP_MaBienThe variant_id, MAX(o.SP_MaSP) product_id,
               MAX(o.SP_SKU) sku, MAX(o.SP_Ten) ten,
               SUM(CASE WHEN o.TaoLuc >= %s THEN o.SP_SL ELSE 0 END) q28,
               SUM(CASE WHEN o.TaoLuc >= %s THEN o.SP_SL ELSE 0 END) q60,
               SUM(o.SP_SL) q90,
               SUM(CASE WHEN o.TaoLuc >= %s THEN {C.REVENUE_EXPR} ELSE 0 END) r28,
               CAST(MAX(o.TaoLuc) AS date) last_sold
        FROM Haravan_DonHang_ChiTiet o
        WHERE {_order_filter()} AND o.TaoLuc >= %s AND o.TaoLuc < %s
        GROUP BY o.MaLocation, o.SP_MaBienThe""",
        (d28, d60, d28, d90, as_of + timedelta(days=1)))


def inventory():
    """Tồn kho snapshot mới nhất (chỉ dòng có tồn hoặc hàng đang về)."""
    return query("""
        SELECT snapshotDate, loc_id, locName, variant_id, product_id, productCode, fullName,
               categoryName, vendor, qty_onhand, qty_available, qty_incoming
        FROM Haravan_TonKho
        WHERE snapshotDate = (SELECT MAX(snapshotDate) FROM Haravan_TonKho)
          AND (qty_onhand <> 0 OR qty_incoming <> 0)""")


def variant_master():
    return query("""
        SELECT DISTINCT variant_id, product_id, productCode, fullName, categoryName
        FROM Haravan_TonKho WHERE snapshotDate = (SELECT MAX(snapshotDate) FROM Haravan_TonKho)""")


def dormant_customers(as_of: date):
    """Số KH cũ (mua 61–365 ngày trước, chưa quay lại) theo cửa hàng – cho hoạt động CRM."""
    return query(f"""
        SELECT MaLocation, COUNT(*) n FROM (
            SELECT o.MaLocation, o.KH_SDT, MAX(o.TaoLuc) last_buy
            FROM Haravan_DonHang_ChiTiet o
            WHERE {_order_filter()} AND o.KH_SDT IS NOT NULL AND o.TaoLuc >= %s
            GROUP BY o.MaLocation, o.KH_SDT) x
        WHERE last_buy < %s GROUP BY MaLocation""",
        (as_of - timedelta(days=365), as_of - timedelta(days=60)))


def combo_effect(as_of: date):
    """Bill có voucher combo/mua nhiều vs bill thường (90 ngày) theo cửa hàng."""
    return query(f"""
        SELECT o.MaLocation,
               CASE WHEN o.Voucher LIKE '%%COMBO%%' OR o.Voucher LIKE 'MUA%%' THEN 1 ELSE 0 END combo,
               COUNT(DISTINCT o.MaDon) bills, SUM(o.SP_SL) units, SUM({C.REVENUE_EXPR}) rev
        FROM Haravan_DonHang_ChiTiet o
        WHERE {_order_filter()} AND o.TaoLuc >= %s AND o.TaoLuc < %s
        GROUP BY o.MaLocation, CASE WHEN o.Voucher LIKE '%%COMBO%%' OR o.Voucher LIKE 'MUA%%' THEN 1 ELSE 0 END""",
        (as_of - timedelta(days=89), as_of + timedelta(days=1)))
