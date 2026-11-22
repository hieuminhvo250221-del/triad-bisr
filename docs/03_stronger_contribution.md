# Nghiên cứu sâu: làm đóng góp mạnh hơn (2026-11-22)

Cách làm: 6 agent nghiên cứu song song (tài liệu ECC + dự phòng; SRAM điện áp thấp; lý thuyết phủ đỉnh
có ràng buộc; kiến trúc spare và thu lỗi; phương pháp đánh giá; baseline nguồn mở), cộng ba thí nghiệm
tôi tự chạy trên máy này. Mục 5 ghi rõ điều nào tôi đã tự kiểm chứng, điều nào mới là lời của agent.

## 1. Kết luận

Hướng mạnh nhất còn khả thi là **ba trụ cùng lúc**:

1. **Lý thuyết.** Bài toán "hàng + cột + ECC có ngân sách K" là một biến thể chưa ai phát biểu của
   Constrained Bipartite Vertex Cover (CBVC). Các kết quả có thể đưa vào paper:
   - NP-khó với mọi K cố định (K = 0 chính là CBVC; K >= 1 cần viết chứng minh, agent đề xuất phép nhân bản K+1 lần).
   - Nhân (kernel) `R + S(R+K) + K` từ, chặt; là dạng có K của kernel `2*kA*kB` kinh điển (Jansen, STACS 2016).
   - Giải được trong `O(3^(R+S))`; và **đa thức khi S cố định**: duyệt mọi tập cột (466 tập với W=30, S=2),
     mỗi tập chỉ cần đếm. Thực tế S <= 2, nên "chính xác" là rẻ - khớp với số nút tìm kiếm rất nhỏ đã đo.
   - Ví dụ nhỏ nhất mà heuristic tham lam của ta sai (tìm bằng vét cạn): R=0, S=1, K=2, ba từ có bit lỗi
     {0}, {2}, {1,2}; lời giải đúng là thay cột 2.
2. **Kiến trúc: lái cột theo phân vùng địa chỉ** làm tài nguyên thứ tư. Bảng tra theo các bit địa chỉ cao
   cho biết mỗi cột dự phòng thay bit nào trong từng phân vùng; một cột dự phòng sửa được một bit khác
   nhau ở mỗi phân vùng, hoặc cùng một bit ở mọi phân vùng (đứt bit-line). Bài toán tách theo phân vùng,
   từ dự phòng và ngân sách K vẫn chung, giải chính xác bằng quy hoạch động.
3. **Đánh giá theo chuẩn của tài liệu** và so trực tiếp với autoMBIST trên cùng macro.

Đóng góp sau khi thêm vẫn là mức hội nghị khu vực, chưa phải mức tạp chí: không có silicon, bộ nhớ nhỏ.

## 2. Số đo của lái cột theo phân vùng (256x30, S=2 cột dự phòng)

Số khuyết tật mỗi bộ nhớ chịu được ở tỉ lệ sửa 90 %. P = số phân vùng (P=1 là sơ đồ hiện tại).

| Hỗn hợp lỗi | K | P=1 | P=4 | P=16 | P=64 |
|---|---|---|---|---|---|
| chỉ lỗi cell, R=2 | 0 | 4.1 | 7.5 | 15.9 | 37.2 |
| chỉ lỗi cell, R=2 | 8 | 13.6 | 18.6 | 35.2 | hơn 40 |
| mixed, R=2 | 0 | 3.2 | 4.4 | 5.6 | 6.5 |
| mixed, R=2 | 8 | 8.3 | 9.2 | 9.3 | 9.4 |

Với K = 0 (không hy sinh chút bảo vệ soft-error nào), P=16 chịu được gấp 3.9 lần số lỗi cell.

**So ở cùng số flip-flop** (từ dự phòng = 39 FF; bảng phân vùng = P x S x 6 FF), K = 0:

| Cấu hình | FF | chỉ lỗi cell | mixed | 80 % cell + 10 % hàng + 10 % cột |
|---|---|---|---|---|
| P=1, R=7 | 273 | 9.6 | 7.0 | 7.5 |
| P=4, R=6 | 282 | 13.6 | 8.4 | 7.7 |
| P=8, R=4 | 252 | 15.1 | 7.5 | 6.4 |
| P=16, R=2 | 270 | 15.8 | 5.5 | 4.3 |
| P=1, R=9 | 351 | 12.3 | 8.5 | 9.3 |
| P=16, R=4 | 348 | 22.1 | 8.2 | 6.5 |

Đọc bảng này cho đúng: phân vùng **không phải lúc nào cũng thắng**. Khi lỗi cell chiếm đa số, nó hơn
60-80 % so với dùng cùng diện tích cho từ dự phòng. Khi có từ 10 % lỗi đường trở lên, từ dự phòng đáng
giá hơn, và cấu hình lai (P=4) chỉ nhỉnh hơn khoảng 20 % ở `mixed`. Vì vậy đóng góp đúng là **một không
gian thiết kế có ràng buộc diện tích và công cụ chọn (P, R, S, K) theo hỗn hợp lỗi**, không phải "kiến
trúc mới luôn tốt hơn".

Cơ chế đã có: Rab, Bawa, Touba, "Improving Memory Repair by Selective Row Partitioning", DFTS 2009
(trong mảng nhớ, cấu hình bằng cầu chì). Phần chưa thấy công bố: hiện thực bằng wrapper mềm quanh hard
macro không có spare, và phân bổ đồng thời với từ dự phòng và ngân sách ECC.

## 3. Hướng đã loại: tự sửa để hạ điện áp (Vmin)

Ý tưởng: lỗi cell tăng theo hàm mũ khi hạ VDD, đúng vùng nhiều lỗi mà sơ đồ của ta có lợi; lợi ích quy ra
công suất. Tôi chạy thử SPICE trên chính bitcell của macro (`model/analysis/bitcell_probe.py`): 200 cell,
góc `tt_mm` (có mismatch cục bộ), 25 C, xung word-line 5 ns, driver lý tưởng.

| VDD (V) | 1.8 - 0.7 | 0.6 | 0.5 |
|---|---|---|---|
| Lỗi đọc (lật khi đọc) / 200 | 0 | 0 | 0 |
| Lỗi ghi / 200 | 0 | 73 | 199 |

- Điểm tốt: PDK mở **có** mô hình mismatch cho transistor SRAM; 200 cell chạy trong khoảng 10 giây.
- Lý do loại: bitcell không lỗi tới 0.7 V, rồi sụp trong khoảng 0.1 V. Thư viện cell chuẩn sky130 chỉ
  đặc tả tới 1.28 V, và macro mới chỉ được đo hoạt động ở 1.7-1.8 V (OpenRAM OR1, ISCAS 2023; giữ dữ
  liệu tới 0.44 V). Vùng có lỗi cell nằm ngoài vùng ký duyệt được timing/công suất, nên lợi ích công suất
  sẽ chỉ là suy đoán. Giữ thí nghiệm này làm căn cứ cho mô hình lỗi, không làm đóng góp chính.
- Phép thử này chỉ cho bậc độ lớn: 200 mẫu, một nhiệt độ, không có mạch ngoại vi.

## 4. Những điều làm thay đổi cách viết paper

- **Sửa ở mức wrapper cho macro không có spare không phải là mới**: Tessent "External Repair" làm đúng
  việc này (một IO dư + mux dịch bit), autoMBIST cũng có remap ngoài macro.
- **Có BIRA phần cứng tận dụng ECC từ 2011**: Sun et al., ISAS 2011. Phải trích và so sánh.
- Theo agent, các điểm sau **chưa thấy công bố**: ngân sách K theo số từ trong bộ phân bổ chính xác;
  bước mua lại để tối thiểu số từ tiêu ECC; must-repair cột có ECC (Lv 2021 chỉ có cho hàng); chặn trên
  bộ lưu lỗi có K. Rủi ro còn lại: toàn văn bài Siemens ETS 2024 và hai bằng sáng chế của Arm.
- Giao thức đánh giá nên theo tài liệu: 10 000 mẫu mỗi điểm; báo cả repair rate và normalized repair
  rate; dùng nhiều hỗn hợp lỗi đã công bố thay cho hỗn hợp tự đặt; yield theo Poisson và nhị thức âm.
- Hội nghị hợp phạm vi nhất: ITC-Asia (có mục memory test and repair), ATS, ISOCC; dễ hơn: ATC, ICCE.

## 5. Mức độ kiểm chứng

Tôi tự kiểm chứng:
- Mọi con số ở mục 2 và 3 (script trong `model/analysis/`, chạy lại được).
- Tồn tại và nội dung tóm tắt của: Sun et al. ISAS 2011; Jansen STACS 2016; OpenRAM OR1 ISCAS 2023
  (khoảng 40 MHz, giữ dữ liệu tới 440 mV); Touba DFTS 2009.
- "Đa thức khi S cố định": tự lập luận lại, đúng.
- Ví dụ phản chứng tham lam do agent đưa ra là **sai** (bài toán đó không sửa được); ví dụ ở mục 1 là
  do tôi tìm lại bằng vét cạn.
- Agent báo không thấy mô hình mismatch cho transistor SRAM; kiểm tra trên máy thì **có**.

Mới là lời của agent, chưa kiểm chứng:
- Chứng minh NP-khó với K >= 1 (mới là phác thảo).
- Hai bằng sáng chế Arm (US 11,315,654; US 11,862,271), EEMR (ITC 2012), bài ITC 2026 về HBM, bộ
  benchmark RA của ITC 2020.
- Các tỉ lệ hỗn hợp lỗi "chuẩn" (nhóm Kang 80.4/9.7/9.7 và 44.8/27.8/27.4; DATE 2006 40/20/20/20; Öhler d1-d3).
- Chi tiết autoMBIST (giới hạn R, C; số liệu diện tích/tần số chưa thấy công bố).

## 6. Việc phát sinh nếu chọn hướng ba trụ

- Viết chứng minh NP-khó và chặn chặt (có ví dụ đạt chặn, kiểm bằng máy).
- RTL: bảng lái cột theo phân vùng (tham số P) và bộ phân bổ hai lượt; giữ P=1 làm cấu hình cơ sở.
- Mô hình vàng: đưa phân vùng vào `model/triad/` kèm test vét cạn (hiện mới là script khảo sát).
- Chạy lại Monte Carlo theo giao thức chuẩn; cài autoMBIST làm baseline.
