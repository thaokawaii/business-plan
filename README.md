# Business Plan tuần tự động – Giám sát & Cửa hàng

Sinh file Excel kế hoạch + checklist **theo tuần, 1 file/giám sát**, mỗi cửa hàng 1 sheet,
từ SQL Server `KiotViet_Thailand`: `Haravan_DonHang_ChiTiet` (bán), `targetVN` (target tháng), `Haravan_TonKho` (tồn).
Mặc định xuất **mô hình kết hợp**: OGSM (chiến lược) → Driver Tree + 4DX (thực thi bán hàng S1, S2, S4) → OTB + PDCA (hàng hóa S3).
Vẫn có thể xuất riêng từng mô hình (m1, m2, m3) để đối chiếu.

## Chạy

```bash
pip3 install -r requirements.txt
cp .env.example .env      # điền thông tin kết nối (file .env không được commit)
python3 run.py                         # tuần kế tiếp, mô hình kết hợp
python3 run.py --week 2026-11-16       # chỉ định thứ Hai đầu tuần
python3 run.py --model all             # kết hợp + 3 mô hình riêng
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
| Doanh thu | `SP_ThanhTien` các đơn không `cancel`, không `refunded/voided` (chỉnh trong `config.py`) |
| Target tuần/ngày | (Target tháng − Lũy kế) phân bổ cho các ngày còn lại theo **trọng số thứ** (8 tuần gần nhất; T7–CN ≈ 1,45×) |
| Driver | Doanh số = Bill × ATV; ATV = UPT × Giá TB/SP; benchmark = trung vị chuỗi 28 ngày |
| Dự báo tháng | Lũy kế + nhịp TB 28 ngày × trọng số ngày còn lại → XANH ≥100%, VÀNG 85–100%, ĐỎ <85% |
| Tồn kho | cover = tồn / bán TB ngày (28N); bổ sung khi cover < 7 ngày lên mức 21 ngày; tồn chậm = có tồn, 0 bán 60 ngày; mẫu top 30 chuỗi CH không có; điều chuyển CH dư (>90 ngày) → CH thiếu cùng giám sát |

## 3 mô hình

Mô tả chi tiết từng mô hình: [docs/MO_TA_3_MO_HINH.md](docs/MO_TA_3_MO_HINH.md)

| | M1 – KPI Driver Tree + 4DX | M2 – OGSM cascade | M3 – Merchandise/OTB + PDCA |
|---|---|---|---|
| Nguồn gốc | Retail KPI tree (chuỗi bán lẻ) + *4 Disciplines of Execution* (FranklinCovey) | P&G, Coca-Cola, Nestlé, Heineken | Merchandise planning chuỗi thời trang/giày; PDCA (Deming) |
| Câu hỏi trả lời | *Thiếu target vì bill, UPT hay giá?* | *Chiến lược nào, đo bằng gì, ai làm?* | *Có đúng hàng, đủ hàng để bán không?* |
| Nội dung sheet CH | WIG, driver tree vs chuỗi, phân rã gap, bảng điểm ngày, lead measures, bổ sung/tồn chậm | O, G, 4 chiến lược S1–S4 mỗi cái có dashboard M + action plan | OTB theo nhóm hàng, bổ sung, điều chuyển, tồn chậm, checklist hàng hóa, Act |
| Mạnh | Chẩn đoán sắc, hành vi bán hàng, nhịp ngày | Dễ trình bày cấp trên, thống nhất vùng → CH | Tồn kho, dòng hàng, điều chuyển |
| Yếu | Ít góc hàng hóa chiến lược | Ít phân tích sâu | Ít tác động hành vi bán |

Gợi ý: M1 làm nhịp vận hành chính; lấy phần OTB/điều chuyển của M3 làm phụ lục hàng hóa.

## Giới hạn dữ liệu
- Không có traffic (lượt khách vào) → chưa tính được tỷ lệ chuyển đổi; M1 đã đặt checklist ghi nhận traffic.
- Không có giá vốn → chưa tính GMROI/biên lợi nhuận.
- POS cửa hàng trên Haravan từ 23/03/2026; tồn kho snapshot từ 30/10/2026.
