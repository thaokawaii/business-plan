"""Cấu hình nghiệp vụ – chỉnh tại đây, không cần sửa code."""

# Doanh thu dòng hàng. Lựa chọn:
#   "SP_ThanhTien"                      – thành tiền dòng (mặc định)
#   "SP_ThanhTien - ISNULL(SP_Giam,0)"  – trừ giảm giá dòng
REVENUE_EXPR = "SP_ThanhTien"

# Loại trừ đơn theo trạng thái
EXCLUDE_ORDER_STATUS = ("cancel",)
EXCLUDE_PAYMENT_STATUS = ("refunded", "voided")

# None = tính mọi kênh có MaLocation của cửa hàng (pos + shopee/tiktok giao từ CH).
# Ví dụ chỉ tính bán tại quầy: INCLUDE_CHANNELS = ("pos",)
INCLUDE_CHANNELS = None

# Kho tổng dùng làm nguồn bổ sung hàng (theo locName trong Haravan_TonKho)
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
