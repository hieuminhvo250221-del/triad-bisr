# 07 — Chi phí độ tin cậy của việc sửa lỗi bằng ECC (FIT)

Mã: `model/triad/reliability.py`, `model/analysis/fit_report.py`. Số liệu: `results/reliability/`.
Chạy lại: `PYTHONPATH=model python model/analysis/fit_report.py build/proto build/export/reliability`.

## Mô hình

Chỉ xét upset đơn bit, độc lập, tốc độ λ mỗi bit-giờ. Không mô hình hoá upset nhiều bit (MBU).

- **Từ sạch** (n = 30 bit mã): hỏng khi hai upset tích luỹ trong thời gian sống T của dữ liệu:
  tốc độ `C(n,2)·λ²·T`, bị phát hiện (DUE).
- **Từ tiêu ECC** (một bit lỗi cứng): lỗi cứng chỉ là lỗi khi bit lưu khác giá trị kẹt (xác suất kích
  hoạt a = 1/2 với dữ liệu ngẫu nhiên). Khi đó một upset ở n−1 bit còn lại thành lỗi kép:
  tốc độ `a·(n−1)·λ` (DUE). Hai upset trong T thành lỗi ba: `a·C(n−1,2)·λ²·T`; bộ giải mã (30,24)
  sửa sai 93,1 % số mẫu lỗi ba (vét cạn 4060 mẫu), phần đó là lỗi im lặng (SDC).

## Giả định số

assumptions: 1000 FIT/Mbit, lifetime 8760 h, activation 0.5. Chưa có số đo soft-error cho macro này; FIT tỉ lệ thuận với giá trị giả định ở số hạng chính.
Thiết kế không có bộ scrub, nên T là thời gian giữa hai lần ghi lại.

## Kết quả

- 256x30 memory, no consumed word: DUE 9.755e-07 FIT, SDC 0.000e+00 FIT
- each consumed word adds: DUE 0.01450 FIT, SDC 1.656e-09 FIT
- 256x24 memory without ECC: SDC 6.144 FIT
- Số hạng chính tuyến tính theo số từ tiêu ECC E, nên ngân sách K chặn trên DUE ở K × 0,0145 FIT
  (K = 8: 0,116 FIT).

Hỗn hợp `mixed`, R = 2, S = 2, K = 8, 10 000 bản đồ mỗi điểm. E là trung bình trên các die sửa được
của từng thuật toán; cột "TRIAD cùng die" là E của TRIAD không phân vùng trên đúng các die mà baseline
sửa được.

| Khuyết tật | Thuật toán | Tỉ lệ sửa | E | TRIAD cùng die | FIT DUE |
|---|---|---|---|---|---|
| 4 | TRIAD | 0,986 | 0,44 | | 0,0064 |
| 4 | TRIAD-P16 | 0,986 | 0,03 | | 0,0004 |
| 4 | ECC-trước, không mua lại | 0,828 | 4,63 | 0,41 | 0,0672 |
| 8 | TRIAD | 0,914 | 4,47 | | 0,0648 |
| 8 | TRIAD-P4 | 0,930 | 1,51 | | 0,0219 |
| 8 | TRIAD-P16 | 0,930 | 0,53 | | 0,0076 |
| 8 | ECC-trước + mua lại | 0,687 | 4,33 | 4,27 | 0,0628 |
| 8 | ECC-trước, không mua lại | 0,245 | 6,69 | 3,88 | 0,0970 |
| 12 | TRIAD | 0,373 | 7,22 | | 0,1046 |
| 12 | TRIAD-P16 | 0,788 | 1,27 | | 0,0185 |

Nhận xét:
- Trên cùng die, TRIAD dùng ít từ ECC hơn ECC-trước rõ rệt khi ít khuyết tật (0,41 so với 4,63), và
  gần bằng "ECC-trước + mua lại" (4,27 so với 4,33); khác biệt với baseline sau nằm ở tỉ lệ sửa.
- Bộ tham lam cùng công thức cho E gần như bằng bộ chính xác (xem `fit_summary.csv`).
- Phân vùng giảm E mạnh nhất: P16 giảm khoảng 8 lần ở 8 khuyết tật.
- "ECC-trước" ở đây là `ef_exact` (ECC trước, rồi phân tích spare chính xác, không mua lại). Các baseline
  ECC-trước được cài theo mô tả tóm tắt của EBISR, chưa đối chiếu toàn văn bài gốc.
