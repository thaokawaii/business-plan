# Tài liệu mô tả 3 mô hình Business Plan tuần

*Áp dụng cho: Giám sát vùng (GS) và Cửa hàng trưởng (CHT)*
*Nguồn số liệu: `Haravan_DonHang_ChiTiet` (bán hàng), `targetVN` (target tháng), `Haravan_TonKho` (tồn kho)*

---

## Mục lục

1. [Tổng quan & cách đọc tài liệu](#1-tổng-quan--cách-đọc-tài-liệu)
2. [Nền tảng số liệu dùng chung](#2-nền-tảng-số-liệu-dùng-chung)
3. [Mô hình 1 – KPI Driver Tree + 4DX](#3-mô-hình-1--kpi-driver-tree--4dx)
4. [Mô hình 2 – OGSM](#4-mô-hình-2--ogsm)
5. [Mô hình 3 – Merchandise / Open-to-Buy + PDCA](#5-mô-hình-3--merchandise--open-to-buy--pdca)
6. [So sánh & khuyến nghị lựa chọn](#6-so-sánh--khuyến-nghị-lựa-chọn)
7. [**Mô hình kết hợp – bản triển khai chính thức**](#7-mô-hình-kết-hợp--bản-triển-khai-chính-thức)
8. [Thuật ngữ](#8-thuật-ngữ)

---

## 1. Tổng quan & cách đọc tài liệu

Hệ thống tự động sinh **business plan tuần** cho từng giám sát. Mỗi file Excel gồm:

- **1 sheet tổng quan vùng** của giám sát,
- **1 sheet cho mỗi cửa hàng**: phân tích, mục tiêu, và **checklist hành động** có người phụ trách, hạn, trạng thái.

Cùng một bộ số liệu được trình bày theo **3 mô hình quản trị** đang được dùng phổ biến trên thế giới. Mỗi mô hình nhìn vấn đề "làm sao đạt target" từ một góc khác:

| Mô hình | Câu hỏi trung tâm | Góc nhìn |
|---|---|---|
| **M1 – Driver Tree + 4DX** | Thiếu target vì **thiếu khách (bill)**, **bill nhỏ (UPT)** hay **giá thấp**? | Hành vi bán hàng |
| **M2 – OGSM** | **Chiến lược** nào, **đo** bằng gì, **ai làm**? | Chiến lược & phân công |
| **M3 – Merchandise / OTB + PDCA** | Có **đúng hàng, đủ hàng** để bán không? | Hàng hóa & tồn kho |

Mục tiêu của tài liệu: giúp người duyệt hiểu **mỗi mô hình là gì, vận hành thế nào, file Excel thể hiện ra sao**, từ đó chọn mô hình (hoặc kết hợp) để triển khai.

> **Trạng thái hiện tại:** hệ thống chỉ xuất **file mô hình kết hợp** (mục 7). Các mục 3–5 mô tả phương pháp của từng mô hình thành phần; phần "cấu trúc file" ở các mục đó là bản thử nghiệm ban đầu, không còn được xuất riêng.
>
> **Thay đổi:** số liệu bán hàng chỉ tính **kênh POS**. Phần "điều chuyển lẻ từng size giữa cửa hàng" đã **bỏ**, vì làm cửa hàng chuyển đi bị lủng size. Thay bằng phân tích theo **mẫu đủ size**, **đặc tính khu vực**, **mùa vụ** và **sự kiện** (mục 7.5).

---

## 2. Nền tảng số liệu dùng chung

Cả 3 mô hình dùng chung một "engine" tính toán, nên **số liệu giữa các mô hình luôn khớp nhau**. Chỉ cách trình bày và cách hành động khác nhau.

### 2.1. Nối dữ liệu

| Bảng | Cột khóa cửa hàng |
|---|---|
| Đơn hàng | `MaLocation` |
| Target | `MaLocation` |
| Tồn kho | `loc_id` |

- **Doanh thu** = tổng `SP_ThanhTien` của các đơn **kênh POS** (bán tại quầy), **không hủy**, **không hoàn tiền/void**.
- Có thể đổi kênh hoặc cách tính (vd "trừ giảm giá dòng") trong `config.py`.
- Công cụ dụng cụ, vật tư trưng bày, bao bì (mã `CCDC…`, phom giày, túi nilong/túi giấy…) được **loại khỏi** phân tích tồn kho.

### 2.2. Target tuần và target ngày

Target trong `targetVN` là target **tháng**. Hệ thống chuyển thành target tuần/ngày như sau:

1. **Phần còn thiếu** = Target tháng − Doanh số lũy kế đến hôm qua.
2. Phần còn thiếu được chia cho **các ngày còn lại trong tháng** theo **trọng số từng thứ trong tuần**.
3. Trọng số lấy từ doanh số thực tế 8 tuần gần nhất của toàn chuỗi:

| T2 | T3 | T4 | T5 | T6 | T7 | CN |
|---|---|---|---|---|---|---|
| 0,83 | 0,80 | 0,77 | 0,83 | 0,87 | **1,44** | **1,46** |

> Ví dụ: target ngày Chủ nhật lớn gần gấp đôi thứ Tư, vì thực tế cuối tuần bán gấp đôi.
>
> Ưu điểm của cách chia này: nếu tuần trước hụt, phần hụt tự động dồn vào target các tuần sau. Cửa hàng luôn thấy con số "cần làm" thật sự để về đích tháng.

### 2.3. Dự báo cuối tháng và trạng thái

- **Dự báo** = Lũy kế + (doanh số TB ngày của 28 ngày gần nhất × trọng số các ngày còn lại).
- **Trạng thái** theo dự báo so với target:

| Trạng thái | Điều kiện |
|---|---|
| 🟢 XANH | Dự báo ≥ 100% target |
| 🟡 VÀNG | Dự báo 85–100% target |
| 🔴 ĐỎ | Dự báo < 85% target |

### 2.4. Các chỉ số bán hàng

| Chỉ số | Công thức | Ý nghĩa |
|---|---|---|
| Số bill | Số đơn khác nhau | Lượt khách mua |
| ATV | Doanh số ÷ Số bill | Giá trị trung bình 1 bill |
| UPT | Số SP ÷ Số bill | Số sản phẩm trên 1 bill |
| Giá TB/SP (ASP) | Doanh số ÷ Số SP | Giá bán trung bình 1 sản phẩm |
| Trung vị chuỗi | Giá trị ở giữa của tất cả cửa hàng (28 ngày) | Chuẩn so sánh công bằng, không bị kéo lệch bởi cửa hàng quá tốt/quá kém |

### 2.5. Các chỉ số tồn kho

| Chỉ số | Công thức / Quy tắc | Ngưỡng mặc định |
|---|---|---|
| Cover (ngày) | Tồn ÷ bán TB/ngày (28 ngày) | Mục tiêu 21 ngày |
| Cần bổ sung | SKU bán ≥ 2 trong 28 ngày và cover dưới ngưỡng. SL đề xuất = đưa về mức tồn mục tiêu, trừ hàng đang về | Cover < 7 ngày |
| Tồn chậm | Có tồn nhưng không bán | 60 ngày |
| Tồn dư | Cover vượt ngưỡng | > 90 ngày |
| Mẫu top thiếu | Mẫu trong **top 30 bán chạy toàn chuỗi** mà cửa hàng không có tồn | — |
| Mẫu đủ size | Gợi ý hàng hóa ở cấp **mẫu-màu**, nhận/luân chuyển **nguyên dải size**; không chuyển lẻ từng size | ≥ 3 size |
| Size lẻ | Mẫu còn < 3 size và không bán 60 ngày: gom khu xả, KM tại chỗ hoặc trả kho | < 3 size |

> Tất cả ngưỡng đều chỉnh được trong `config.py`.

---

## 3. Mô hình 1 – KPI Driver Tree + 4DX

### 3.1. Mô hình là gì

Mô hình kết hợp hai phương pháp:

**a) Retail KPI Driver Tree (cây chỉ số bán lẻ)**

Đây là cách phân tích chuẩn của các chuỗi bán lẻ. Doanh số được **tách thành các yếu tố cấu thành (driver)**:

```
Doanh số
├── Số bill (lượt mua)        ← (Traffic × Tỷ lệ chuyển đổi, nếu có đếm khách)
└── ATV (giá trị 1 bill)
    ├── UPT (số SP/bill)
    └── Giá TB/SP
```

- Khi doanh số hụt, ta không nói chung chung "cần bán nhiều hơn".
- Ta chỉ ra cụ thể **driver nào đang yếu**. Mỗi driver có cách xử lý rất khác nhau:
  - Thiếu bill → kéo khách.
  - UPT thấp → bán kèm.
  - Giá thấp → upsell.

**b) 4DX – The 4 Disciplines of Execution (FranklinCovey)**

Phương pháp **thực thi** được nhiều tập đoàn bán lẻ và dịch vụ dùng. Gồm 4 nguyên tắc:

| # | Nguyên tắc | Áp dụng trong file |
|---|---|---|
| 1 | Tập trung vào **WIG** (Wildly Important Goal – mục tiêu quan trọng nhất) | Mỗi cửa hàng có **1 câu WIG** cho tuần |
| 2 | Hành động theo **lead measures** (chỉ số dẫn dắt) | Số bill, UPT, số KH được gọi lại… là những thứ nhân viên **tác động được hằng ngày**. Doanh số chỉ là **lag measure** (kết quả) |
| 3 | Giữ **bảng điểm** (scoreboard) dễ thấy | Bảng điểm ngày: cửa hàng tự nhập thực tế mỗi tối |
| 4 | Tạo **nhịp trách nhiệm** đều đặn | Họp đầu ca 10 phút mỗi ngày; GS họp WIG 20 phút với CHT đầu tuần |

### 3.2. Cách vận hành

**Bước 1 – Xác định khoảng thiếu (gap).** So sánh:
- Doanh số trung bình **4 tuần gần nhất** (nền), với
- **Target tuần**.

**Bước 2 – Đặt mục tiêu cho từng driver.**

| Driver | Cách đặt mục tiêu |
|---|---|
| UPT | Tăng tối thiểu **+3%**; nếu thấp hơn trung vị chuỗi thì kéo dần về trung vị, tối đa **+15%**/tuần |
| Giá TB/SP | Tăng tối thiểu **+2%**; nếu thấp hơn trung vị thì kéo về trung vị, tối đa **+5%** |
| Số bill | **Phần còn lại**: Bill cần = Target tuần ÷ ATV mục tiêu |

**Bước 3 – Phân rã gap.** Hệ thống tính phần tăng/giảm doanh số do từng driver đóng góp. Ví dụ: *"Số bill −27,3 tr · UPT +17,7 tr · Giá TB +2,5 tr"*.

**Bước 4 – Sinh hành động tự động theo quy tắc:**

| Tình huống phát hiện | Hành động được đưa vào checklist |
|---|---|
| Bill mục tiêu > bill hiện tại | Mục tiêu bill/tuần, ưu tiên T7–CN |
| Bill mục tiêu > bill hiện tại, và CH có khách cũ | Gọi/nhắn Zalo khách cũ không quay lại 60–365 ngày (tối đa 140 KH/tuần) |
| Bill mục tiêu > bill hiện tại | Mời khách giờ cao điểm; ghi nhận traffic |
| UPT cần tăng | Bán kèm vớ / lót giày / thắt lưng / ví; kèm tỷ trọng phụ kiện hiện tại |
| Giá TB thấp hơn chuỗi | Upsell dòng cao cấp, trưng bày ngang tầm mắt |
| Có SKU bán chạy sắp hết | Đặt bổ sung (kèm danh sách SKU) |
| Thiếu mẫu top chuỗi | Đề xuất nhận mẫu |
| Có tồn chậm | Đưa ra kệ đầu, thi đua bán, combo |
| Luôn có | Họp đầu ca; họp WIG tuần |

### 3.3. Cấu trúc file Excel

**Sheet "Tổng quan vùng"**

- Khối chỉ số vùng: target tháng, lũy kế, dự báo, target tuần, cần tăng bao nhiêu %, số cửa hàng đỏ.
- **Bảng xếp hạng cửa hàng** (cửa hàng kém nhất lên đầu). Mỗi dòng có: trạng thái, % dự báo, cần/ngày, target tuần, bill mục tiêu, UPT mục tiêu, **driver gap chính**, số SKU cần bổ sung, số SKU tồn chậm.
- Checklist việc của giám sát.
- (Bản kết hợp) gợi ý hàng hóa theo mẫu đủ size, xem mục 7.6.

**Sheet từng cửa hàng** (theo thứ tự từ trên xuống):

1. Khối chỉ số tháng: trạng thái, target, lũy kế, dự báo, cần/ngày, TB 7 ngày.
2. **WIG**. Ví dụ: *"Đạt 101,3 tr doanh số tuần = 55 bill × ATV 1,9 tr (UPT 2,13 × giá TB 0,9 tr)"*.
3. **Driver tree**: so sánh 7 ngày qua / TB 4 tuần / trung vị chuỗi / mục tiêu tuần / % thay đổi cần, cho từng chỉ số.
4. **Bảng điểm ngày** (T2 → CN):
   - Hệ thống điền sẵn: target ngày.
   - Cửa hàng nhập (ô vàng): thực tế, số bill, số SP.
   - Tự tính: % đạt, lũy kế, UPT; tô màu xanh/vàng/đỏ.
5. **Checklist lead measures**: đòn bẩy, hành động, KPI, chỉ tiêu, phụ trách, hạn, trạng thái (dropdown ☐ / ◐ / ☑ / ✖), ghi chú kết quả.
6. Danh sách SKU cần bổ sung · Mẫu top chuỗi đang thiếu · Danh sách tồn chậm.

### 3.4. Nhịp làm việc trong tuần

| Thời điểm | Ai | Việc |
|---|---|---|
| Thứ Hai, đầu tuần | GS + CHT | Họp WIG 20': xem driver tree, chốt lead measures, phân công checklist |
| Mỗi sáng | CHT + nhân viên | Họp đầu ca 10': xem bảng điểm hôm qua, mỗi người cam kết 1 việc |
| Mỗi tối | CHT | Nhập thực tế, bill, SP vào bảng điểm; cập nhật trạng thái checklist |
| Chủ nhật | GS | Tổng hợp bảng điểm các cửa hàng, chuẩn bị họp tuần sau |

### 3.5. Ví dụ thực tế – CH2 HN 12 THÁI HÀ, tuần 09–15/11/2026

| Chỉ số | TB 4 tuần | Trung vị chuỗi | Mục tiêu tuần |
|---|---|---|---|
| Doanh số/tuần | 108,4 tr | — | 101,3 tr |
| Số bill/tuần | 68 | — | 55 |
| UPT | 1,85 | 2,34 | 2,13 |
| Giá TB/SP | 0,9 tr | 0,66 tr | 0,9 tr |

**Đọc kết quả:**
- Cửa hàng có giá TB **cao hơn** chuỗi, nhưng UPT **thấp hơn** chuỗi rõ rệt.
- Hành động chính là **bán kèm phụ kiện** để kéo UPT, thay vì giảm giá hay chạy theo số bill.

### 3.6. Ưu điểm – Hạn chế

| ✅ Ưu điểm | ⚠️ Hạn chế |
|---|---|
| Chẩn đoán chính xác nguyên nhân hụt target, đến từng driver | Ít góc nhìn chiến lược dài hạn, ví dụ mở rộng khách hàng mới |
| Hành động gắn với chỉ số nhân viên tác động được mỗi ngày | Cần cửa hàng **kỷ luật nhập bảng điểm**, nếu không sẽ mất hiệu quả |
| Nhịp ngày/tuần rõ ràng, dễ kiểm tra | Chưa có traffic nên chưa tách được "ít khách vào" hay "khách vào không mua" |
| | Hàng hóa chỉ ở mức danh sách, chưa có kế hoạch nhập theo nhóm hàng |

**Phù hợp khi:** muốn **điều hành bán hàng hằng ngày** và tạo thói quen thực thi ở cửa hàng.

---

## 4. Mô hình 2 – OGSM

### 4.1. Mô hình là gì

**OGSM = Objective – Goals – Strategies – Measures.**

- Xuất phát từ Nhật Bản/Mỹ thập niên 1950–60.
- Được **Procter & Gamble** phổ biến, sau đó Coca-Cola, Nestlé, Heineken, Unilever… dùng rộng rãi.
- Đặc trưng: **cả kế hoạch nằm gọn trên 1 trang** và **cascade (phân tầng)**. OGSM cấp trên trở thành mục tiêu của cấp dưới.

| Thành phần | Ý nghĩa | Đặc điểm |
|---|---|---|
| **O – Objective** | Mục tiêu tổng, định tính | 1 câu, truyền cảm hứng, trả lời "chúng ta muốn đạt điều gì" |
| **G – Goals** | Mục tiêu định lượng | Con số đo được, có thời hạn (target) |
| **S – Strategies** | Chiến lược / đòn bẩy | 3–5 lựa chọn "chúng ta sẽ thắng bằng cách nào" |
| **M – Measures** | Đo lường + kế hoạch hành động | (a) **Dashboard**: chỉ số theo dõi từng chiến lược; (b) **Action plan**: việc cụ thể, người phụ trách, hạn |

### 4.2. Cách vận hành trong hệ thống

**Cascade 2 tầng:**

```
OGSM VÙNG (Giám sát)
  O: Vùng đạt 100% target tháng, không CH nào dưới 85%
  G: Doanh số tháng/tuần vùng, số CH xanh, số CH đỏ
  S: S1–S4 (bên dưới)
  M: Bảng chỉ số S1–S4 theo từng CH + việc của GS
      │
      ▼
OGSM CỬA HÀNG (từng CH)
  O: Đưa CH về nhịp đạt 100% target tháng
  G: Doanh số tuần, doanh số tháng, số bill, ATV
  S1–S4, mỗi S có dashboard M + action plan riêng
```

**4 chiến lược chuẩn** (giống nhau cho mọi cửa hàng, để giám sát so sánh được):

| Chiến lược | Dashboard đo lường (M) | Hành động tiêu biểu |
|---|---|---|
| **S1. Tăng lượt mua (số bill)** | Bill/tuần hiện tại → mục tiêu; số KH cũ có thể gọi lại | CRM gọi KH cũ, mời khách giờ cao điểm, đếm traffic |
| **S2. Tăng giá trị bill** | UPT, Giá TB/SP, ATV, tỷ trọng phụ kiện | Bán kèm, upsell dòng cao cấp |
| **S3. Hàng hóa đúng – đủ – bán được** | SKU bán chạy sắp hết, mẫu top thiếu, SP tồn chậm, cover | Bổ sung, nhận mẫu đủ size, xử lý size lẻ, đẩy tồn chậm |
| **S4. Kỷ luật thực thi** | Doanh số tuần, số ngày cập nhật bảng điểm | Họp đầu ca, họp tuần với GS |

Hành động trong M2 lấy từ cùng bộ quy tắc ở M1, nhưng được **xếp theo chiến lược** thay vì theo driver.

### 4.3. Cấu trúc file Excel

**Sheet "OGSM vùng"**

- O (1 câu) và G (bảng mục tiêu vùng).
- Bảng **S & M theo cửa hàng**: target tuần; S1 bill hiện tại → mục tiêu; S2 UPT hiện tại → mục tiêu; S3 số SKU cần bổ sung, SP tồn chậm.
- Action plan của giám sát.
- Gợi ý hàng hóa theo khu vực (mục 7.5).

**Sheet từng cửa hàng**

- O → G.
- Với mỗi S1…S4:
  - **M dashboard**: hiện tại / chỉ tiêu / ô nhập thực tế cuối tuần.
  - **M action plan**: checklist có trạng thái.
- Bảng theo dõi ngày.
- Phụ lục S3: danh sách SKU bổ sung, mẫu top thiếu.

### 4.4. Nhịp làm việc

| Thời điểm | Ai | Việc |
|---|---|---|
| Đầu tuần | GS | Trình bày OGSM vùng; thống nhất S1–S4 với các CHT |
| Trong tuần | CHT | Thực hiện action plan theo từng S |
| Cuối tuần | CHT | Nhập "thực tế cuối tuần" cho từng chỉ số M |
| Cuối tuần | GS | Đánh giá chiến lược nào hiệu quả, chiến lược nào cần đổi trọng tâm |
| Cuối tháng | Quản lý | Dùng OGSM vùng để báo cáo |

### 4.5. Ưu điểm – Hạn chế

| ✅ Ưu điểm | ⚠️ Hạn chế |
|---|---|
| **Dễ trình bày** với cấp trên, ban giám đốc. Ngôn ngữ chiến lược quen thuộc | Phân tích số liệu nông hơn M1, không thấy rõ driver nào là nguyên nhân chính |
| Thống nhất vùng → cửa hàng: mọi người cùng 4 chiến lược | Nhịp theo tuần, ít công cụ bám sát hằng ngày |
| Rõ "ai làm gì" theo từng mục tiêu | Dễ thành "điền form" nếu GS không thật sự review chiến lược |
| Phù hợp mở rộng lên cấp miền/công ty | |

**Phù hợp khi:** cần **một ngôn ngữ kế hoạch thống nhất** từ công ty → vùng → cửa hàng, và báo cáo cho cấp quản lý.

---

## 5. Mô hình 3 – Merchandise / Open-to-Buy + PDCA

### 5.1. Mô hình là gì

Mô hình kết hợp hai phương pháp:

**a) Merchandise Planning / Open-to-Buy (OTB)**

Phương pháp lập kế hoạch **dẫn dắt bởi hàng hóa**, chuẩn của các chuỗi thời trang, giày dép, phụ kiện quốc tế. Nguyên lý: *muốn bán được thì hàng phải đúng mẫu, đúng size, đủ số lượng, đúng nơi*.

**Open-to-Buy** = lượng hàng được phép nhập thêm:

```
OTB (SL) = Kế hoạch bán trong kỳ + Tồn mục tiêu cuối kỳ − Tồn hiện có − Hàng đang về
```

Các chỉ số then chốt:

| Chỉ số | Ý nghĩa |
|---|---|
| **Sell-through (ST%)** | Bán ÷ (Bán + Tồn). Hàng có "chạy" không |
| **Cover / Weeks of supply** | Tồn đủ bán bao nhiêu ngày |
| **Tồn chậm / tồn dư** | Vốn bị "chôn", cần giải phóng |
| **Thiếu mẫu, thiếu size** | Doanh số bị mất vì không có hàng |

**b) PDCA (chu trình Deming)**

**Plan – Do – Check – Act.** Vòng cải tiến liên tục, nền tảng của Lean/Kaizen (Toyota) và ISO.

### 5.2. Cách vận hành trong hệ thống

**P – PLAN (Lập kế hoạch hàng hóa)**

1. **SL cần bán trong tuần** = Target tuần ÷ Giá TB/SP mục tiêu.
2. Chia SL này theo **nhóm hàng** (Moccasin, Loafer, Sandals, Vớ…) theo tỷ trọng bán 28 ngày.
3. Mỗi nhóm hàng tính:
   - **OTB** = Kế hoạch bán tuần + tồn mục tiêu 21 ngày − tồn − đang về.
   - **Tồn dư** = phần vượt quá 90 ngày bán.
4. Gắn nhãn hành động cho từng nhóm hàng:

| Nhãn | Khi nào |
|---|---|
| **BỔ SUNG** | Có OTB > 0 và cover thấp |
| **XẢ / LUÂN CHUYỂN NGUYÊN MẪU** | Có tồn dư |
| **OK** | Còn lại |

**D – DO (Thực hiện)**

- Bổ sung SKU bán chạy sắp hết, kèm cột "Kho tổng có" để biết lấy hàng từ đâu.
- Nhận mẫu top chuỗi chưa có.
- **Nhận mẫu đủ size** đang bán tốt ở cửa hàng cùng khu vực; **xử lý size lẻ** tại chỗ (không chuyển lẻ).
- Đẩy hàng tồn chậm.

**C – CHECK (Kiểm tra)**

- Bảng điểm ngày (doanh số, bill, SP).
- **Checklist hàng hóa trong tuần:**

| # | Việc | Thời điểm |
|---|---|---|
| 1 | Kiểm đếm hàng bán chạy, đối chiếu tồn hệ thống | T2 |
| 2 | Gửi đề xuất bổ sung/OTB cho GS & kho tổng | T2 |
| 3 | Đổi layout, đưa tồn chậm ra kệ đầu | T3 |
| 4 | Nhận hàng, lên kệ trong 24h | T4 |
| 5 | Đủ size cho mẫu top 10 | T5 |
| 6 | Đếm lại sell-through nhóm hàng chính | CN |

**A – ACT (Điều chỉnh)**

Bảng rút kinh nghiệm, cửa hàng tự nhập: *Điều gì hiệu quả / Điều gì chưa / Điều chỉnh tuần sau / Phụ trách*. Đây là đầu vào cho kế hoạch tuần kế tiếp.

### 5.3. Cấu trúc file Excel

**Sheet "Tổng quan vùng"**

- **Sức khỏe tồn kho theo cửa hàng**: tồn, cover, ST%, SKU cần bổ sung, mẫu top thiếu, SKU/SP tồn chậm, % tồn chậm. Cửa hàng tồn nặng nhất lên đầu.
- **Ma trận nhóm hàng toàn vùng**: doanh số, bán, tồn, đang về, cover, ST%.
- **Gợi ý luân chuyển nguyên mẫu** theo khu vực, GS quyết định.

**Sheet từng cửa hàng:** khối chỉ số hàng hóa → P (bảng OTB nhóm hàng) → D (4 danh sách) → C (bảng điểm + checklist) → A (rút kinh nghiệm).

### 5.4. Nhịp làm việc

| Thời điểm | Ai | Việc |
|---|---|---|
| Thứ Hai | CHT | Kiểm đếm, gửi đề xuất OTB/bổ sung |
| Thứ Hai | GS | Duyệt đề xuất nhận mẫu đủ size, phương án size lẻ |
| T3–T5 | CHT | Nhận hàng, lên kệ, đổi layout, kiểm tra size |
| Chủ nhật | CHT | Đếm sell-through, ghi phần Act |
| Đầu tuần sau | GS | Dùng phần Act để điều chỉnh kế hoạch |

### 5.5. Ưu điểm – Hạn chế

| ✅ Ưu điểm | ⚠️ Hạn chế |
|---|---|
| Giải quyết **mất doanh số do thiếu hàng/thiếu size**, rất quan trọng với ngành giày | Ít tác động đến **hành vi bán hàng** (mời khách, bán kèm) |
| Giải phóng **vốn tồn chậm**, giảm hàng dư | Phụ thuộc độ chính xác tồn kho hệ thống. Dữ liệu tồn mới có từ 30/10/2026 |
| Gợi ý theo mẫu đủ size, khu vực, mùa vụ | Chưa có giá vốn nên chưa tính GMROI (lãi gộp trên tồn kho) |
| PDCA tạo thói quen cải tiến | Nặng việc kho/vận hành hơn cho CHT |

**Phù hợp khi:** vấn đề chính là **hàng hóa**: thiếu mẫu bán chạy, tồn kho nặng, phân bổ hàng giữa cửa hàng chưa tốt.

---

## 6. So sánh & khuyến nghị lựa chọn

### 6.1. Bảng so sánh

| Tiêu chí | M1 – Driver Tree + 4DX | M2 – OGSM | M3 – Merch/OTB + PDCA |
|---|---|---|---|
| Nguồn gốc | Chuỗi bán lẻ + FranklinCovey | P&G, Coca-Cola, Nestlé | Chuỗi thời trang/giày + Toyota/Deming |
| Trọng tâm | Hành vi bán hàng | Chiến lược & phân công | Hàng hóa & tồn kho |
| Độ sâu phân tích | ★★★ | ★★ | ★★★ (riêng hàng hóa) |
| Dễ trình bày cấp trên | ★★ | ★★★ | ★★ |
| Theo dõi hằng ngày | ★★★ | ★ | ★★ |
| Khối lượng việc cho CHT | Trung bình | Thấp | Cao |
| Yêu cầu dữ liệu | Bán hàng | Bán hàng + tồn | Tồn kho phải chính xác |

### 6.2. Khi nào chọn mô hình nào

| Nếu vấn đề chính là… | Chọn |
|---|---|
| Cửa hàng có hàng nhưng **bán không ra**, nhân viên thiếu nhịp, UPT thấp | **M1** |
| Cần **thống nhất kế hoạch** toàn hệ thống và báo cáo lên trên | **M2** |
| **Thiếu mẫu/size bán chạy**, tồn chậm nhiều, hàng phân bổ lệch | **M3** |

### 6.3. Khuyến nghị

Theo số liệu hiện tại:
- Đa số cửa hàng hụt target do **số bill thấp**.
- Nhiều cửa hàng có UPT dưới trung vị chuỗi.
- Đồng thời mỗi cửa hàng có hàng trăm SKU tồn chậm.

Vì vậy đề xuất **kết hợp**:

> **M1 làm khung vận hành chính** (WIG, driver tree, bảng điểm ngày, lead measures)
> **\+ phần OTB/hàng hóa của M3 làm phụ lục hàng hóa**
> **\+ dùng sheet "OGSM vùng" của M2 để báo cáo cấp trên hằng tháng.**

Nên **chạy thử 2–4 tuần** ở 1–2 vùng, sau đó chọn mô hình chính thức dựa trên phản hồi của GS/CHT và mức cải thiện bill, UPT.

### 6.4. Lưu ý trước khi áp dụng

1. **Target đang cao hơn nhiều so với nhịp bán hiện tại.** Dự báo hiện đạt khoảng 26–44% target ở các vùng. Cần xác nhận:
   - Doanh thu trên Haravan đã đầy đủ chưa (POS cửa hàng chỉ có từ 23/03/2026)?
   - Cách tính doanh thu có khớp cách đặt target không?
2. **Chưa có đếm khách (traffic).** Nên lắp hoặc ghi nhận số khách vào cửa để tính tỷ lệ chuyển đổi. Đây là driver quan trọng nhất còn thiếu.
3. **Chưa có giá vốn**, nên chưa tối ưu được theo lợi nhuận.

---

## 7. Mô hình kết hợp – bản triển khai chính thức

### 7.1. Nguyên tắc

Ba mô hình **không thay thế nhau**. Mỗi mô hình giải một bài toán ở một tầng khác nhau, và được ghép thành một hệ thống:

```
OGSM  ─ khung chiến lược (đi đâu, thắng bằng gì, đo bằng gì)
 ├── S1. Tăng lượt mua (số bill)        ┐
 ├── S2. Tăng giá trị bill (UPT × giá)  ├─ thực thi bằng Driver Tree + 4DX
 ├── S4. Kỷ luật thực thi               ┘
 └── S3. Hàng hóa đúng – đủ – bán được  ── thực thi bằng OTB + PDCA
```

| Tầng | Mô hình | Vai trò |
|---|---|---|
| Chiến lược | **OGSM** | Đặt mục tiêu O/G và 4 chiến lược S1–S4, thống nhất từ vùng xuống cửa hàng |
| Thực thi bán hàng | **Driver Tree + 4DX** | Chẩn đoán driver, mục tiêu tuần (WIG), bảng điểm ngày, lead measures |
| Thực thi hàng hóa | **OTB + PDCA** | Kế hoạch hàng theo nhóm, mẫu đủ size, size lẻ, mùa vụ, sự kiện, xả tồn chậm |
| Cải tiến | **PDCA (Act) + họp WIG** | Đánh giá từng chiến lược cuối tuần, điều chỉnh tuần sau |

Mọi hành động trong file đều mang **mã chiến lược S1–S4**, ví dụ *"S2 · UPT (SP/bill)"*. Nhờ đó luôn biết việc đó phục vụ chiến lược nào.

> **Lưu ý về OTB:** hiện OTB tính theo **số lượng sản phẩm**, vì dữ liệu chưa có giá vốn. Tức là mô hình đang kiểm soát *lượng hàng/tồn kho*, chưa kiểm soát *tiền hàng*. Khi bổ sung giá vốn, có thể nâng lên OTB theo giá trị và GMROI.

### 7.2. Cấu trúc file (1 file / giám sát / tuần)

| Sheet | Nội dung | Mô hình |
|---|---|---|
| **Hướng dẫn** | Cấu trúc mô hình, nhịp làm việc, quy ước ô nhập | — |
| **OGSM vùng** | O, G vùng; bảng S1–S4 × từng cửa hàng (hiện tại → mục tiêu); việc của GS | OGSM |
| **Điều hành bán hàng** | Xếp hạng cửa hàng theo % dự báo: target, lũy kế, cần/ngày, bill, UPT, ATV, driver gap chính | Driver Tree |
| **Hàng hóa vùng** | Sức khỏe tồn kho & đặc tính từng CH, **xu hướng nhóm hàng theo khu vực**, **lịch sự kiện**, **gợi ý luân chuyển nguyên mẫu** để GS quyết định | OTB |
| **1 sheet / cửa hàng** | 4 mục ① ② ③ ④, xem 7.3 | Cả 3 |

### 7.3. Sheet cửa hàng – 4 mục

**Khối đầu trang:** trạng thái, target tháng, lũy kế, dự báo, target tuần, cần/ngày.

**Đặc tính cửa hàng:** khu vực, loại mặt bằng, mức giá so với chuỗi, % hàng nữ, % phụ kiện, size bán chạy, UPT bill combo/thường, % bill combo, ghi chú mùa vụ, nhóm cửa hàng dùng để so sánh.

**① OGSM cửa hàng**

- **O:** mục tiêu tháng.
- **WIG tuần**. Ví dụ: *101,3 tr = 55 bill × ATV 1,9 tr (UPT 2,13 × giá TB 0,9 tr)*.
- **Bảng G + S1–S4:**

| Cột | Nội dung |
|---|---|
| Chiến lược | G, S1, S2, S3, S4 |
| Chỉ số đo (M) | Ví dụ: số bill, UPT, ATV, SKU sắp hết, SP tồn chậm |
| Hiện tại | Hệ thống điền |
| Mục tiêu tuần | Hệ thống điền |
| Thực tế cuối tuần | **CHT nhập** |
| Công cụ thực thi | Trỏ tới mục ② hoặc ③ |

**② Thực thi bán hàng – Driver Tree + 4DX (S1, S2, S4)**

- Driver tree: 7 ngày qua / TB 4 tuần / trung vị chuỗi / mục tiêu tuần / % thay đổi cần; phân rã gap theo driver.
- **Bảng điểm ngày** T2 → CN: target ngày có sẵn; nhập thực tế, số bill, số SP; tự tính % đạt, lũy kế, UPT.
- Checklist lead measures S1, S2, S4.

**③ Thực thi hàng hóa – OTB + PDCA (S3)**

| Bước | Nội dung |
|---|---|
| **P – Plan** | SL cần bán tuần; bảng OTB theo nhóm hàng (bán, tồn, đang về, cover, ST%, KH bán, OTB cần nhập, tồn dư, nhãn hành động) |
| **D – Do** | Checklist S3; bổ sung SKU sắp hết; mẫu top chuỗi chưa có; cơ hội nhóm hàng; nhận mẫu đủ size; size lẻ; luân chuyển nguyên mẫu; tồn chậm; sự kiện |
| **C – Check** | Checklist kiểm tra hàng hóa theo ngày trong tuần |

**④ Đánh giá tuần (Check – Act)**

Với từng chiến lược S1–S4, CHT nhập:
- Đạt mục tiêu? (Có/Không)
- Điều gì hiệu quả
- Điều gì chưa hiệu quả
- Điều chỉnh tuần sau
- Phụ trách

Bảng này là đầu vào cho **họp WIG thứ Hai** tuần kế tiếp.

### 7.4. Nhịp vận hành

| Thời điểm | Ai | Việc | Phần dùng |
|---|---|---|---|
| Thứ Hai sáng | GS + CHT | Họp WIG 20': xem OGSM CH, driver tree, đánh giá tuần trước, chốt cam kết | ① ② ④ |
| Thứ Hai | CHT → GS | Kiểm đếm, gửi đề xuất bổ sung/OTB | ③ |
| Thứ Hai | GS | Duyệt đề xuất mẫu đủ size, luân chuyển nguyên mẫu, phương án size lẻ | Hàng hóa vùng |
| Mỗi sáng | CHT + NV | Họp đầu ca 10' theo bảng điểm | ② |
| Mỗi tối | CHT | Nhập thực tế, bill, SP; cập nhật trạng thái checklist | ② ③ |
| T3–T5 | CHT | Nhận hàng, lên kệ, đổi layout, kiểm tra size | ③ |
| Chủ nhật | CHT | Nhập thực tế cuối tuần cho G/S1–S4, viết đánh giá | ① ④ |
| Chủ nhật | GS | Tổng hợp vùng, báo cáo cấp trên | OGSM vùng |

### 7.5. Phân tích hàng hóa chuyên sâu (thay cho điều chuyển lẻ size)

**Vì sao bỏ điều chuyển lẻ size:** chuyển 1–2 size của một mã sang cửa hàng khác làm **cửa hàng chuyển đi bị lủng size**: khách đến không có size, mẫu mất khả năng bán. Gợi ý hàng hóa giờ dựa trên phân tích, ở cấp **mẫu-màu đủ dải size**, và **GS là người quyết định**.

| Phân tích | Cách làm | Kết quả trong file |
|---|---|---|
| **Khu vực địa lý** | Mã khu vực trong tên CH: HN, MB, HC, MĐ, MT, TN. Mỗi CH được so với **CH cùng khu vực** (đủ ≥ 3 CH, nếu thiếu thì so toàn chuỗi) | Cột "So sánh với…" |
| **Mùa vụ / khí hậu** | Đặc điểm theo tháng từng khu vực (miền Bắc mùa lạnh 11–2; miền Trung mưa bão 9–12; miền Nam mưa 5–11, khô 12–4…), cấu hình trong `config.py` | Ghi chú mùa vụ + hành động sắp xếp layout |
| **Xu hướng nhóm hàng theo khu vực** | Bán 28 ngày gần nhất so với 28 ngày trước, theo nhóm hàng, trong từng khu vực | Bảng xu hướng ở "Hàng hóa vùng". Ví dụ: Boots ở Hà Nội +77% đầu mùa lạnh |
| **Đặc tính khách hàng** (suy ra từ bán hàng) | Mức giá so với chuỗi, % hàng nữ, % phụ kiện, size bán chạy, hiệu quả combo | Khối "Đặc tính cửa hàng" |
| **Cơ hội nhóm hàng** | Tỷ trọng nhóm của CH so với khu vực, kết hợp xu hướng khu vực | THIẾU / MẠNH / tương đương, kèm hành động |
| **Mẫu nên nhận (đủ size)** | Mẫu bán tốt ở ≥ 2 CH cùng khu vực mà CH không có hoặc chỉ còn < 3 size. **Size nên nhận lấy theo size bán chạy của chính mẫu đó** trong khu vực (vd boots nữ 35–39). Có số size và SL còn ở kho tổng | Bảng đề xuất, GS duyệt |
| **Size lẻ** | Mẫu còn < 3 size, không bán 60 ngày | Chọn phương án: khu xả size lẻ / KM tại chỗ / trả kho tổng / giữ lại. **Không chuyển lẻ** |
| **Luân chuyển nguyên mẫu** | Mẫu còn **đủ dải size** nhưng CH không bán 60 ngày, trong khi khu vực khác bán ≥ 5 đôi/28 ngày và nhóm hàng ở đó không giảm | Gợi ý cho GS quyết định, chuyển **nguyên mẫu** |
| **Sự kiện** | Lịch sự kiện bán lẻ (11.11, 20/11, Black Friday, 12.12, Noel, Tết…). Hiệu ứng đo trên POS: doanh số chuỗi ngày sự kiện ±1 ngày so với TB cùng thứ 4 tuần trước (đã đo: 2/9 ×1,94; 20/10 ×1,39; 10.10 ×1,14) | Bảng sự kiện; sự kiện rơi vào tuần kế hoạch thành hành động S1 |
| **Combo** | UPT bill có voucher combo/mua nhiều so với bill thường (toàn chuỗi khoảng 5,1 so với 2,7) | Hành động S2: tăng % bill combo |

> **Giới hạn:** POS trên Haravan mới đủ từ tháng 6/2026, nên chưa có cùng kỳ năm trước. Sự kiện chưa từng diễn ra trong dữ liệu (11.11, 20/11, Black Friday) ghi "chưa có lịch sử POS". Đặc tính dân cư đang **suy ra từ hành vi mua tại cửa hàng**, chưa có dữ liệu dân số/thu nhập bên ngoài. Có thể bổ sung sau qua `config.py`.

### 7.6. Cách chạy

```bash
python3 run.py                      # mô hình kết hợp, tuần kế tiếp (mặc định)
python3 run.py --week 2026-11-16    # chỉ định thứ Hai đầu tuần
```

Kết quả nằm tại `output/<năm-Wtuần>/KET_HOP_OGSM_4DX_OTB/BP_<tuần>_KETHOP_<giám sát>.xlsx`.

> Chương trình **tự dừng** nếu dữ liệu bán hàng bị thiếu ngày trong 35 ngày gần nhất, ví dụ khi ETL đang nạp lại. Mục đích là tránh xuất kế hoạch sai. Muốn vẫn chạy thì thêm `--allow-gaps`.

---

## 8. Thuật ngữ

| Thuật ngữ | Giải thích |
|---|---|
| **ATV** (Average Transaction Value) | Giá trị trung bình 1 bill |
| **UPT** (Units Per Transaction) | Số sản phẩm trung bình trên 1 bill |
| **ASP** (Average Selling Price) | Giá bán trung bình 1 sản phẩm |
| **Driver** | Yếu tố cấu thành, quyết định doanh số |
| **WIG** (Wildly Important Goal) | Mục tiêu quan trọng nhất cần tập trung |
| **Lead measure** | Chỉ số dẫn dắt: hành động tác động được, dự báo kết quả |
| **Lag measure** | Chỉ số kết quả, ví dụ doanh số: chỉ biết sau khi đã xảy ra |
| **Scoreboard** | Bảng điểm theo dõi tiến độ |
| **Cascade** | Phân tầng mục tiêu từ cấp trên xuống cấp dưới |
| **OTB** (Open-to-Buy) | Lượng hàng còn được phép nhập trong kỳ |
| **Sell-through (ST%)** | Tỷ lệ bán ra trên tổng hàng có |
| **Cover** | Số ngày bán mà lượng tồn hiện tại đáp ứng được |
| **SKU** | Mã hàng chi tiết đến màu/size |
| **Trung vị chuỗi** | Giá trị ở giữa khi xếp tất cả cửa hàng, dùng làm chuẩn so sánh |
| **PDCA** | Plan – Do – Check – Act: vòng cải tiến liên tục |
| **RAG** | Red – Amber – Green: trạng thái đỏ / vàng / xanh |
