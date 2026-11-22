# Pha 1 — Tổng quan tài liệu và cổng G1

Cập nhật: 2026-11-22. Nguồn: tìm kiếm web trong phiên làm việc này. Tôi mới đọc được **tóm tắt và
trích đoạn**, chưa có toàn văn của các bài IEEE. Mục đánh dấu **(M)** là trích theo trí nhớ, phải kiểm
tra lại thông tin thư mục trước khi đưa vào paper.

## 1. Bảng công trình liên quan

### 1.1 Phân tích dự phòng (RA/BIRA) cho dự phòng 2 chiều, không ECC

| # | Công trình | Nội dung chính | Liên hệ với đề tài |
|---|---|---|---|
| 1 | Kuo, Fuchs, IEEE Design & Test 1987 (M) | Chứng minh RA là NP-đầy đủ; must-repair; branch-and-bound | Nền tảng; must-repair của ta là mở rộng có ECC |
| 2 | Kawagoe et al., ITC 2000 — CRESTA (M) | Các bộ phân tích con chạy song song mọi thứ tự hàng/cột; tối ưu, chạy cùng lúc với test | Baseline tối ưu về tỉ lệ sửa; diện tích tăng theo C(R+S, R) |
| 3 | Huang et al., IEEE Trans. Reliability 2003 — LRM, ESP (M) | Heuristic dùng bitmap cục bộ / pivot | Baseline heuristic (ESP); EBISR dùng ESP |
| 4 | Öhler, Hellebrand, Wunderlich, ETS 2007 (M) | Tích hợp BIST và sửa cho dự phòng 2D, tìm kiếm có quay lui | Cùng họ tìm kiếm chính xác nối tiếp |
| 5 | Jeong et al., TVLSI 2009 — SFCC; 2010 — BRANCH (M) | Cây tìm kiếm theo đường (line-based), tối ưu, diện tích nhỏ hơn CRESTA | Cùng họ |
| 6 | Tseng, Li, Chang, DATE 2006; TVLSI 2010 | BIRA cho RAM hướng từ, dùng bitmap cục bộ 1 chiều; overhead ~2.9 % cho 8192x64 | Cùng đối tượng (RAM hướng từ); mốc so sánh overhead |
| 7 | Lee, Park, Kang, ISOCC 2009 | CAM lưu lỗi tiết kiệm diện tích + LFSR | Kỹ thuật lưu lỗi |
| 8 | Lee et al., TCAS-I 2017 | Dùng vùng nhớ không lỗi để lưu thông tin lỗi thay cho CAM | Hướng giảm diện tích khác |
| 9 | TVLSI 2017 — 1-D spare segments | Chia cột dự phòng thành đoạn | Kiến trúc spare khác |
| 10 | Lee, Han, Lee, Kang, TVLSI 2019 — Dynamic BIRA | Phân tích động khi đang test, thu hồi mục CAM; có lời giải ngay khi test xong | Thu hồi CAM động: đã có, không tuyên bố |
| 11 | Han, Kim, Kim, Kang, TVLSI 2025 — SPOT | "Potential case" sinh ngay sau test, vét cạn phần còn lại; tối ưu, thời gian phân tích rất thấp | SOTA về BIRA 2D tối ưu |
| 12 | Cho et al., ACM Computing Surveys 2016 | Khảo sát RA: ba tiêu chí thời gian phân tích, tỉ lệ sửa, diện tích | Khung đánh giá |
| 13 | EWDTS 2024 | Bảng quyết định 8 mẫu sửa cho 2 hàng + 2 cột (3D) | Hướng không tìm kiếm |
| 14 | IJECE 2024 (review) | Tổng quan BISR + ECC | Nguồn mô tả lại EBISR |

### 1.2 Kết hợp ECC với dự phòng — nhóm sát đề tài nhất

| # | Công trình | Nội dung chính | Khác biệt còn lại của đề tài |
|---|---|---|---|
| 15 | Su, Yeh, Wu, DFT 2005 | ECC phát hiện lỗi cứng khi vận hành, dùng spare còn thừa sửa lúc rảnh | Họ làm in-field; ta phân bổ lúc test |
| 16 | **Lu, Tsai, Hashizume, ATS 2015; TVLSI 2016 — EBISR** | ECC sửa lỗi đơn trước, spare (ESP) cho phần còn lại; có giai đoạn online giữ độ tin cậy | Heuristic, không ngân sách ECC, không tối ưu đồng thời |
| 17 | **Lv, Sun, Xin, Zheng, IEEE Trans. Computers 2021** | RA **tối ưu** cho bộ nhớ có spare + in-memory ECC: must-repair theo từ mã, cây tìm kiếm lai, DFS; kèm heuristic tham lam. Phía ATE, DRAM | **Đã có "tối ưu đồng thời spare + ECC"**. Ta khác ở: chạy trên chip, có ngân sách K, tối thiểu số từ tiêu ECC, chặn trên kích thước bộ lưu lỗi |
| 18 | **Han, Lee, Lee, Kang, IEEE Access 2021** | RA khớp mẫu có xét ECC, dừng sớm có xét ECC; nhắm dùng ECC tiết kiệm (độ tin cậy cao hơn 8.6 lần) | Phía ATE, heuristic khớp mẫu; không có ngân sách lập trình được |
| 19 | **Romain et al. (Siemens), ETS 2024; ITC India 2025** | Đưa ECC vào luồng test-sửa chuẩn (Tessent): BIRA bỏ qua số lỗi trong từ không vượt khả năng sửa; đánh đổi do người dùng chọn sau khi có silicon | Công cụ thương mại, đóng; không công bố thuật toán tối ưu hay chặn trên |
| 20 | Kim et al. — tối ưu đồng thời kích thước cell, dự phòng, ECC cho SRAM điện áp thấp (M: nơi đăng) | Mô hình thiết kế, không phải thuật toán BIRA | Động cơ: vùng mật độ lỗi cao |
| 21 | DATE 2007 — SECDED cho soft error và lỗi do biến thiên trong cache | ECC che lỗi cứng, thay khối khi vượt khả năng | Động cơ |
| 22 | VTS 2011 — Programmable extended SEC-DED | Mã mở rộng sửa lỗi kép ở tập vị trí bit chọn được | Hướng mã hoá khác |
| 23 | ATS 2011 — Yield-per-area cho 6T-SRAM với spare + ECC | Mô hình yield/diện tích | Mô hình tham khảo |
| 24 | Lu et al., ASICON 2015 — fault scrambling | Xáo bit lỗi sang các từ mã khác nhau để ECC sửa | Hướng khác |
| 25 | Schöber et al., ITC 2001 — redundant words (M) | Sửa bằng từ dự phòng | Tài nguyên "hàng" của ta chính là từ dự phòng |

### 1.3 Khác

| # | Công trình | Nội dung | Liên hệ |
|---|---|---|---|
| 26 | MIMS, DAC 2011; ISQED 2017 | Sửa gần đúng, ưu tiên bit quan trọng | Hướng B đã loại |
| 27 | TCAD 2019 — in-field self-repair + ECC theo lão hoá | Sửa chủ động khi vận hành | Hướng C đã loại |
| 28 | **autoMBIST, 2026 (GitHub, ORConf 2026)** | Sinh MBIST + BIRA 2D (must-repair + quay lui) + BISR cho OpenRAM sky130, LibreLane, PicoRV32 | **Đã có luồng mở đầy đủ**; không có ECC. Là mốc so sánh nguồn mở |
| 29 | Caravel MPW-3/5 MBIST controller | Chỉ dự phòng hàng, 4 địa chỉ | Mốc cũ |
| 30 | Guthaus et al., OpenRAM, ICCAD 2016 (M) | Trình biên dịch SRAM mở | Macro sử dụng |

## 2. Ma trận tuyên bố sau G1

| Tuyên bố ban đầu | Kết luận | Lý do |
|---|---|---|
| C1 "phân bổ đồng thời 3 tài nguyên, tối ưu" | **Không còn mới ở mức ý tưởng** | [17] đã có RA tối ưu cho spare + ECC; [18] đã nhắm giảm dùng ECC |
| C1' "… **trên chip**, có **ngân sách ECC K lập trình được**, tối thiểu số từ tiêu ECC" | Giữ, mức cải tiến | Chưa thấy BIRA phần cứng nào công bố dạng chính xác có ngân sách; [19] có đánh đổi do người dùng chọn nhưng không công bố thuật toán |
| C2 chặn trên bộ lưu lỗi `R + S(R+K) + K` | Giữ | [17] có must-repair hàng theo từ mã nhưng (theo trích đoạn) không xét must-repair cột và không có chặn trên; chặn của ta đạt được (chặt) |
| C3 tìm kiếm rẽ 3 nhánh sâu `R+S` + mua lại tham lam tối ưu | Giữ, cần so kỹ với "cây tìm kiếm lai" của [17] | Cấu trúc tìm kiếm khác (rẽ theo từ xung đột), phù hợp phần cứng nối tiếp |
| C4 RTL-to-GDS nguồn mở | Chỉ là đóng góp hiện thực + số liệu PPA | [28] đã có luồng mở (không ECC) |

## 3. Kết luận cổng G1: **thu hẹp**

Phát biểu đóng góp nên dùng từ nay:

> Bộ phân bổ dự phòng **tích hợp trên chip** cho SRAM nhúng, giải **chính xác** bài toán ba tài nguyên
> (từ dự phòng, cột dự phòng, ECC) **dưới một ngân sách độ tin cậy lập trình được**, với chặn trên chặt
> cho bộ lưu lỗi và số nút tìm kiếm không quá 3^(R+S); hiện thực RTL-to-GDS nguồn mở trên sky130 và
> định lượng đánh đổi yield – độ tin cậy – PPA.

Không được viết "first joint/optimal ECC + redundancy analysis". Phải trích [16], [17], [18], [19], [28]
và so sánh trực tiếp.

## 4. Việc còn nợ của pha 1

- Đọc toàn văn [16], [17], [18] (cần quyền truy cập IEEE Xplore hoặc bản tác giả) để: so cấu trúc tìm
  kiếm với [17], xác nhận [17] không có chặn trên/ngân sách, và cài lại EBISR đúng nguyên bản.
- Kiểm tra thông tin thư mục các mục (M).
- Tìm thêm công trình 2022–2026 về BIRA phần cứng có ECC (đã tìm hai lượt, chưa thấy).
