# Pha 2 — Mô hình vàng và cổng G2 (Monte Carlo trước khi viết RTL)

Cập nhật: 2026-11-22. Mã: `model/triad/`, kiểm thử: `model/tests/`, phân tích: `model/analysis/g2_report.py`.
Số liệu và hình: `results/g2/`. Chạy lại: xem cuối file.

## 1. Mô hình vàng đã kiểm chứng

- `solver.py`: must-repair có ECC -> tìm kiếm rẽ 3 nhánh -> "mua lại" ECC tham lam; hai chính sách
  (`reliability_first`: tối thiểu số từ tiêu ECC rồi số spare; `spare_saving`: ngược lại).
- So với vét cạn (`core.brute_force`) trên 9 000 bản đồ lỗi ngẫu nhiên, cả hai chính sách:
  kết luận sửa được/không và giá trị mục tiêu **trùng 100 %** (9 test, `pytest` đạt).
- Kiểm tra độ nhạy của test bằng 5 đột biến cố ý (bỏ nhánh cột thứ hai, sai ngưỡng must-repair cột,
  must-repair từ bỏ qua ECC, chặn trên thiếu số hạng K, mua lại chọn cột nhỏ nhất): test phát hiện
  cả 5 (64–700 sai khác), bản gốc 0 sai khác.
- Chặn trên bộ lưu lỗi `R + S(R+K) + K` đúng với mọi bản đồ sửa được đã thử, và **đạt được**
  (ví dụ R=2, S=2, K=8: tối đa quan sát 30 = chặn trên). Bỏ số hạng `S*K` thì sai.
- Công sức tìm kiếm tối đa quan sát: 55 nút (R=2, S=2), 175 nút (R=4, S=2); chặn lý thuyết 3^(R+S).

## 2. Thiết lập thí nghiệm

- Bộ nhớ: 256 từ x 30 bit mã (24 dữ liệu + 6 kiểm tra), mux cột 2 (đúng với macro: `words_per_row: 2`).
  Khuyết tật vật lý: cell, cặp ngang/dọc, cụm 2x2, đứt word-line (chết 2 từ), đứt bit-line (128 từ, mỗi từ 1 bit).
- Ba hỗn hợp: `cells` (100 % cell), `mixed` (70 % cell, 14 % cặp, 6 % cụm, 5 % hàng, 5 % cột), `lines` (50/25/25).
  **Các tỉ lệ này là giả định**, không phải số đo của sky130.
- 5 000 bản đồ lỗi cho mỗi số khuyết tật 1..24; mọi thuật toán nhận cùng bản đồ.
- Thang so sánh (cùng R, S, K): ESP không ECC; 2D chính xác không ECC; ECC-trước + ESP (kiểu EBISR);
  ECC-trước + 2D chính xác; như trên + mua lại; **tham lam đồng thời** (repair-most có xét ECC, không
  quay lui); **TRIAD** (đồng thời, chính xác).
- Tiêu chí định trước khi chạy: (a) yield TRIAD hơn "ECC-trước chính xác + mua lại" ít nhất 1 điểm %
  ở vùng yield 50–99 %; (b) số từ tiêu ECC ít hơn ít nhất 10 % trên các chip cả hai cùng sửa được.
  Baseline "tham lam đồng thời" được thêm **sau** lần xem kết quả đầu tiên, để tách riêng giá trị của
  việc tìm kiếm chính xác.
- Lưu ý: cài đặt ESP và EBISR dựa trên mô tả phổ biến, chưa đối chiếu toàn văn bài gốc; spare được
  coi là không lỗi.

## 3. Kết quả (hỗn hợp `mixed`, R=2 từ dự phòng, S=2 cột dự phòng)

Mức chênh yield (điểm %) của TRIAD so với từng phương án, đo tại mật độ khuyết tật mà TRIAD đạt yield ~90 %:

| K | Khuyết tật/bộ nhớ tại yield 90 % | so tham lam đồng thời | so ECC-trước + mua lại | so kiểu EBISR | so 2D chính xác | Từ tiêu ECC trên cùng các chip: TRIAD / EBISR |
|---|---|---|---|---|---|---|
| 2 | 3.25 | +0.03 | +1.1 | +59.4 | +18.8 | 0.03 / 1.31 |
| 4 | 4.50 | +0.06 | +3.9 | +51.9 | +41.3 | 0.22 / 2.62 |
| 8 | 6.75 | +0.14 | +13.2 | +45.2 | +71.0 | 1.44 / 5.26 |
| 16 | 9.25 | +0.12 | +26.1 | +38.0 | +85.1 | 4.27 / 9.45 |
| không giới hạn | 9.75 | +0.01 | +28.5 | +34.0 | +86.4 | 5.18 / 14.44 |

Các hỗn hợp khác (R=2, S=2): `cells` — TRIAD, tham lam và ECC-trước + mua lại gần như trùng nhau
(chênh dưới 0.1 điểm %); `lines` — TRIAD hơn ECC-trước + mua lại khoảng 2–7 điểm %, và bằng tham lam.
Bảng đầy đủ: `results/g2/g2_gate.csv`.

### Bộ nhớ lớn hơn: 4096 từ x 39 bit (32 dữ liệu + 7 kiểm tra), mux 8, hỗn hợp `mixed`

Chỉ 500 bản đồ lỗi cho mỗi điểm, nên yield tuyệt đối có sai số khoảng +-2 điểm %; chênh lệch giữa các
thuật toán chính xác hơn vì dùng chung bản đồ.

| R, S | K | Khuyết tật tại yield 90 % | so tham lam | so ECC-trước + mua lại | so kiểu EBISR | Từ tiêu ECC trên cùng các chip: TRIAD / EBISR |
|---|---|---|---|---|---|---|
| 8, 2 | 8 | 7.50 | +0.02 | +1.5 | +64.5 | 0.01 / 5.64 |
| 8, 2 | 32 | 9.75 | +0.00 | +4.5 | +47.0 | 1.07 / 11.57 |
| 8, 2 | không giới hạn | 10.50 | +0.04 | +5.3 | +31.8 | 8.69 / 186.75 |
| 8, 4 | 8 | 9.25 | +0.06 | +1.1 | +75.7 | 0.00 / 6.11 |
| 8, 4 | 32 | 10.75 | +0.00 | +2.0 | +49.3 | 0.40 / 12.67 |

- Xu hướng giống bộ nhớ nhỏ: chính xác so với tham lam không quá 0.12 điểm %.
- Không giới hạn K thì kiểu EBISR để ECC gánh cả một bit-line đứt (512 từ): trung bình 187 từ tiêu ECC,
  so với 8.7 của TRIAD trên cùng các chip.
- **K cũng chặn chi phí phần cứng**: với K <= 32 tìm kiếm không quá 27 nút và bộ lưu lỗi không quá 65 từ;
  với K không giới hạn có trường hợp 24 782 nút và 3 083 từ phải lưu.

## 4. Diễn giải

1. **Tìm kiếm chính xác gần như không tăng yield so với heuristic tham lam cùng công thức**: chênh
   tối đa 0.40 điểm % trên cả 48 cấu hình đã thử của bộ nhớ 256x30. Giá trị của "chính xác" là sự bảo đảm (không loại nhầm
   chip sửa được), không phải con số yield trung bình.
2. **Lợi ích lớn đến từ công thức đồng thời**: cho ECC gánh bit lỗi cuối cùng của từ nhiều lỗi sau khi
   cột/hàng đã che phần còn lại. So với ECC-trước + mua lại: +1 đến +28 điểm % khi có lỗi đường; bằng 0
   khi chỉ có lỗi cell. Công thức này đã có trong Lv et al. 2021 (phía ATE, không ngân sách).
3. **Mua lại giảm mạnh phơi nhiễm soft-error so với kiểu EBISR**: ít hơn 55–100 % số từ tiêu ECC.
   Nhưng mua lại tham lam đơn giản đã lấy gần hết lợi ích này (TRIAD chỉ hơn 0–8 %).
4. **Ngân sách K là núm đánh đổi rõ ràng**: K = 2 / 4 / 8 / 16 / không giới hạn chịu được
   3.25 / 4.5 / 6.75 / 9.25 / 9.75 khuyết tật ở yield 90 %; quá K = 16 gần như không thêm được gì.
5. **Quy đổi độ tin cậy**: mỗi từ tiêu ECC có W = 30 bit mà một soft error bất kỳ sẽ thành lỗi không
   sửa được, nên FIT_DUE = E x 30 x lambda_bit. Với giả định 1000 FIT/Mbit (chưa có số đo cho sky130):
   0.03 FIT cho mỗi từ; K = 8 chặn ở 0.24 FIT và 3.1 % số từ mất bảo vệ.

## 5. Kết luận cổng G2

- Tiêu chí (a): **đạt** với `mixed` và `lines`, **không đạt** với `cells`.
- Tiêu chí (b): **không đạt** (0–8 %, dưới ngưỡng 10 %).
- Giá trị riêng của tìm kiếm chính xác so với tham lam: **không đáng kể về yield**.

Hệ quả cho đề tài:
- Giữ kiến trúc (đồng thời + ngân sách K + mua lại), vì đó là nơi có lợi ích đo được.
- Không tuyên bố "thuật toán chính xác cho yield cao hơn heuristic". Tuyên bố đúng là: bảo đảm tối ưu
  với chi phí phần cứng nhỏ (tối đa 55–175 nút tìm kiếm, bộ lưu lỗi có chặn trên chặt).
- Thêm một thí nghiệm PPA quyết định: **chi phí phần cứng của bộ giải chính xác so với bộ tham lam**.
  Nếu chênh lệch diện tích/thời gian nhỏ thì "chính xác" là bảo hiểm gần như miễn phí; nếu lớn thì
  tham lam là lựa chọn hợp lý hơn và paper phải nói vậy.

## 6. Chạy lại

```bash
cd model
python -m triad.mc --preset macro --trials 5000 --out ../build/g2/macro.csv
python -m triad.mc --preset large --mixes cells mixed --trials 500 --out ../build/g2/large.csv
cd .. && python model/analysis/g2_report.py build/g2/macro.csv build/g2/large.csv --out build/export/g2
```
