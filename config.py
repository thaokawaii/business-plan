"""Cấu hình nghiệp vụ – chỉnh tại đây, không cần sửa code."""

# Doanh thu dòng hàng. Lựa chọn:
#   "SP_ThanhTien"                      – thành tiền dòng (mặc định)
#   "SP_ThanhTien - ISNULL(SP_Giam,0)"  – trừ giảm giá dòng
REVENUE_EXPR = "SP_ThanhTien"

# Loại trừ đơn theo trạng thái
EXCLUDE_ORDER_STATUS = ("cancel",)
EXCLUDE_PAYMENT_STATUS = ("refunded", "voided")

# Kênh bán tính doanh số cửa hàng. ("pos",) = chỉ bán tại quầy.
# None = mọi kênh có MaLocation của cửa hàng (pos + shopee/tiktok giao từ CH).
INCLUDE_CHANNELS = ("pos",)

# Kho tổng dùng làm nguồn cấp hàng (theo locName trong Haravan_TonKho)
WAREHOUSES = ("TỔNG KHO", "Kho trung gian", "Kho Amilo", "Kho Amilo Hà Nội")

# Ngưỡng tồn kho
TARGET_COVER_DAYS = 21      # mức tồn mục tiêu (ngày bán)
LOW_COVER_DAYS = 7          # dưới mức này -> cần bổ sung
OVERSTOCK_COVER_DAYS = 90   # trên mức này -> tồn dư
SLOW_MOVER_DAYS = 60        # có tồn nhưng không bán trong N ngày -> tồn chậm
TOP_N_LIST = 20             # số dòng tối đa mỗi danh sách SKU

# Ngưỡng đánh giá
RAG_GREEN = 1.00            # dự báo đạt >= 100% target
RAG_AMBER = 0.85            # 85–100% vàng, < 85% đỏ
BENCH_GAP = 0.95            # chỉ số < 95% trung vị chuỗi -> cần cải thiện

# Nhóm hàng bán kèm (để gợi ý tăng UPT)
ADDON_CATEGORIES = ("Vớ nam", "Lót giày nam", "Thắt lưng nam", "Bóp - ví nam", "Khác")

# Loại khỏi phân tích tồn kho/hàng hóa: công cụ dụng cụ, vật tư trưng bày, bao bì (không phải hàng bán)
NON_MERCH_SKU_PREFIXES = ("CCDC", "FORMGIAY", "PCTUIE", "PCBUTBI")
NON_MERCH_NAME_KEYWORDS = ("túi nilong", "móc treo", "cây trưng", "trưng giày", "trưng túi", "phom giày",
                           "hoa trang trí", "bút bi", "kệ trưng", "standee", "túi giấy")
MIN_ITEM_PRICE = 30000      # bỏ quà tặng/bao bì (giá TB < mức này) khỏi gợi ý mẫu

# ---------------------------------------------------------------- Phân tích địa lý / sự kiện
# Mã khu vực = token thứ 2 trong tên cửa hàng (vd "CH2 HN AEON HÀ ĐÔNG" -> HN)
REGIONS = {
    "HN": "Hà Nội", "MB": "Miền Bắc (tỉnh)", "HC": "TP.HCM", "MĐ": "Miền Đông (BD, ĐN)",
    "MT": "Miền Tây (ĐBSCL)", "TN": "Miền Trung – Tây Nguyên",
}
# Đặc điểm khí hậu theo tháng (gợi ý định tính; số liệu xu hướng nhóm hàng mới là căn cứ chính)
CLIMATE = {
    "HN": {(11, 12, 1, 2): "Mùa lạnh – ưu tiên giày kín, boots, moccasin lót, vớ cổ cao; giảm sandals/dép",
           (3, 4): "Nồm ẩm – giày da dễ mốc, ưu tiên sneaker/giày vải, chất liệu dễ vệ sinh",
           (5, 6, 7, 8): "Nóng, mưa rào – sandals, dép, giày lười thoáng khí",
           (9, 10): "Thu mát – giao mùa, đẩy giày tây/loafer, chuẩn bị hàng đông"},
    "MB": {(11, 12, 1, 2): "Mùa lạnh – ưu tiên giày kín, boots, vớ cổ cao; giảm sandals/dép",
           (3, 4): "Nồm ẩm – ưu tiên chất liệu dễ vệ sinh",
           (5, 6, 7, 8): "Nóng, mưa rào – sandals, dép, giày lười thoáng khí",
           (9, 10): "Thu mát – giao mùa, chuẩn bị hàng đông"},
    "TN": {(9, 10, 11, 12): "Mùa mưa bão (duyên hải miền Trung) – giày kín, chống nước, hạn chế da lộn",
           (1, 2, 3, 4, 5, 6, 7, 8): "Nắng nóng – sandals, giày lười thoáng khí"},
    "HC": {(5, 6, 7, 8, 9, 10, 11): "Mùa mưa – giày dễ lau, sandals quai chắc, hạn chế da lộn",
           (12, 1, 2, 3, 4): "Mùa khô nóng – sandals, dép, loafer nhẹ"},
    "MĐ": {(5, 6, 7, 8, 9, 10, 11): "Mùa mưa – giày dễ lau, sandals quai chắc",
           (12, 1, 2, 3, 4): "Mùa khô nóng – sandals, dép, loafer nhẹ"},
    "MT": {(5, 6, 7, 8, 9, 10, 11): "Mùa mưa/nước nổi – sandals, dép, giày dễ lau",
           (12, 1, 2, 3, 4): "Mùa khô nóng – sandals, dép, loafer nhẹ"},
}
# Lịch sự kiện bán lẻ: (MM-DD hoặc YYYY-MM-DD, tên, gợi ý nhóm hàng/hoạt động)
EVENTS = [
    ("01-01", "Tết Dương lịch", "Giày mới năm mới, quà tặng"),
    ("2027-02-06", "Tết Nguyên đán 2027 (mùng 1)", "Cao điểm 3 tuần trước Tết: giày mới, ví, thắt lưng, quà biếu"),
    ("02-14", "Valentine", "Quà đôi: ví, thắt lưng, nước hoa, túi nữ"),
    ("03-08", "Quốc tế Phụ nữ", "Giày/túi nữ, nước hoa nữ"),
    ("04-30", "Lễ 30/4 – 1/5", "Du lịch: sandals, dép, sneaker"),
    ("06-01", "Quốc tế Thiếu nhi / giữa năm", "Mid-year sale"),
    ("09-02", "Quốc khánh 2/9", "Nghỉ lễ – du lịch, sale"),
    ("09-09", "Ngày đôi 9.9", "Sale online & tại quầy"),
    ("10-10", "Ngày đôi 10.10", "Sale"),
    ("10-20", "Phụ nữ Việt Nam 20/10", "Giày/túi nữ, quà tặng"),
    ("11-11", "Ngày đôi 11.11", "Sale"),
    ("11-20", "Nhà giáo Việt Nam 20/11", "Quà tặng: ví, thắt lưng, nước hoa, giày tây"),
    ("BLACKFRIDAY", "Black Friday", "Combo mua 2–3, xả tồn chậm"),
    ("12-12", "Ngày đôi 12.12", "Sale"),
    ("12-24", "Giáng sinh", "Quà tặng, boots, hàng đông"),
]
EVENT_LOOKAHEAD_DAYS = 35   # hiển thị sự kiện trong N ngày tới tính từ đầu tuần kế hoạch
PEER_MIN_STORES = 3         # nhóm so sánh = CH cùng khu vực (đủ số CH), nếu thiếu dùng toàn chuỗi
MIN_SIZES_FULL_RUN = 3      # mẫu có ít hơn N size còn hàng = "size lẻ"
