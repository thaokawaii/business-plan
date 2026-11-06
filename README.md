# Business Plan tuần tự động – Giám sát & Cửa hàng

Sinh file Excel kế hoạch + checklist **theo tuần, 1 file/giám sát**, mỗi cửa hàng 1 sheet,
từ SQL Server `KiotViet_Thailand`: `Haravan_DonHang_ChiTiet` (bán), `targetVN` (target tháng), `Haravan_TonKho` (tồn).
Xuất **mô hình kết hợp**: OGSM (chiến lược) → Driver Tree + 4DX (thực thi bán hàng S1, S2, S4) → OTB + PDCA (hàng hóa S3).
Số liệu bán hàng **chỉ tính kênh POS**. Hàng hóa được gợi ý ở cấp **mẫu đủ size** theo khu vực, mùa vụ, sự kiện (không chuyển lẻ size).

## Chạy

```bash
pip3 install -r requirements.txt
cp .env.example .env      # điền thông tin kết nối (file .env không được commit)
python3 run.py                         # tuần kế tiếp, mô hình kết hợp
python3 run.py --week 2026-11-16       # chỉ định thứ Hai đầu tuần
python3 run.py --gs "Kim Ngân"         # chỉ 1 giám sát
python3 run.py --allow-gaps            # vẫn chạy khi dữ liệu bán thiếu ngày (ETL đang nạp)
```

Kết quả: `output/<năm-Wtuần>/KET_HOP_OGSM_4DX_OTB/BP_<tuần>_KETHOP_<giám sát>.xlsx`.
Cấu trúc file kết hợp: xem mục 7 trong [docs/MO_TA_3_MO_HINH.md](docs/MO_TA_3_MO_HINH.md).
Ô **vàng** là ô nhập (thực tế ngày, bill, SP, ghi chú); cột *Trạng thái* là dropdown ☐/◐/☑/✖.

## Logic dùng chung (`bp/metrics.py`)

| Bước | Cách tính |
|---|---|
| Khóa nối | `MaLocation` (đơn) = `MaLocation` (target) = `loc_id` (tồn) |
| Doanh thu | `SP_ThanhTien` kênh **POS**, đơn không `cancel`, không `refunded/voided` (chỉnh trong `config.py`) |
| Target tuần/ngày | (Target tháng − Lũy kế) phân bổ cho các ngày còn lại theo **trọng số thứ** (8 tuần gần nhất; T7–CN ≈ 1,45×) |
| Driver | Doanh số = Bill × ATV; ATV = UPT × Giá TB/SP; benchmark = trung vị chuỗi 28 ngày |
| Dự báo tháng | Lũy kế + nhịp TB 28 ngày × trọng số ngày còn lại → XANH ≥100%, VÀNG 85–100%, ĐỎ <85% |
| Tồn kho | cover = tồn / bán TB ngày (28N); bổ sung khi cover < 7 ngày lên mức 21 ngày; tồn chậm = có tồn, 0 bán 60 ngày; mẫu top 30 chuỗi CH không có; loại công cụ dụng cụ/bao bì |
| Hàng hóa chuyên sâu (`bp/insights.py`) | so với CH cùng khu vực; xu hướng nhóm hàng theo khu vực; mùa vụ; lịch sự kiện & hiệu ứng đo trên POS; hiệu quả combo; đề xuất nhận **mẫu đủ size** (size theo mẫu); **size lẻ** xử lý tại chỗ; **luân chuyển nguyên mẫu** do GS quyết định |

## 3 mô hình

Mô tả chi tiết từng mô hình: [docs/MO_TA_3_MO_HINH.md](docs/MO_TA_3_MO_HINH.md)

| | M1 – KPI Driver Tree + 4DX | M2 – OGSM cascade | M3 – Merchandise/OTB + PDCA |
|---|---|---|---|
| Nguồn gốc | Retail KPI tree (chuỗi bán lẻ) + *4 Disciplines of Execution* (FranklinCovey) | P&G, Coca-Cola, Nestlé, Heineken | Merchandise planning chuỗi thời trang/giày; PDCA (Deming) |
| Câu hỏi trả lời | *Thiếu target vì bill, UPT hay giá?* | *Chiến lược nào, đo bằng gì, ai làm?* | *Có đúng hàng, đủ hàng để bán không?* |
| Vai trò trong bản kết hợp | Thực thi bán hàng (S1, S2, S4) | Khung chiến lược | Thực thi hàng hóa (S3) |
| Mạnh | Chẩn đoán sắc, hành vi bán hàng, nhịp ngày | Dễ trình bày cấp trên, thống nhất vùng → CH | Tồn kho, mẫu đủ size, mùa vụ |
| Yếu | Ít góc hàng hóa chiến lược | Ít phân tích sâu | Ít tác động hành vi bán |

Hệ thống hiện chỉ xuất bản **kết hợp** cả 3 (xem mục 7 tài liệu).

## Giới hạn dữ liệu
- Không có traffic (lượt khách vào) → chưa tính được tỷ lệ chuyển đổi; M1 đã đặt checklist ghi nhận traffic.
- Không có giá vốn → chưa tính GMROI/biên lợi nhuận.
- POS cửa hàng trên Haravan đủ từ 06/2026 (chưa có cùng kỳ năm trước); tồn kho snapshot từ 30/10/2026.
- Đặc tính dân cư suy ra từ hành vi mua tại CH; chưa có dữ liệu dân số/thu nhập bên ngoài.
