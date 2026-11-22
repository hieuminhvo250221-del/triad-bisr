# Kết quả theo giao thức đánh giá (2026-11-22)

Bộ nhớ 256 x 30 bit mã, mux 2, S = 2 cột dự phòng. 10 000 bản đồ lỗi cho mỗi số khuyết tật 1..30, mọi
thuật toán nhận cùng bản đồ. Số liệu: `results/protocol/protocol_summary.csv`, hình: cùng thư mục.
Chạy lại: `python -m triad.mc --preset protocol ...` rồi `model/analysis/protocol_report.py`.

Hỗn hợp lỗi: `kang_dl` (80 % cell, 10 % hàng, 10 % cột), `kang_dh` (45/28/27), `date06` (40 % cell,
40 % cặp, 20 % cụm 2x2), `mixed` (hỗn hợp tự đặt). Ba hỗn hợp đầu lấy theo lời agent tìm tài liệu,
**chưa đối chiếu bài gốc**.

## Số khuyết tật chịu được ở tỉ lệ sửa 90 % (R = 2 từ dự phòng)

| Hỗn hợp | K | TRIAD-P 16 vùng | TRIAD-P 4 vùng | TRIAD không phân vùng | ECC-trước + mua lại | 2D chính xác, không ECC | ESP, không ECC |
|---|---|---|---|---|---|---|---|
| date06 | 0 | 8.3 | 4.4 | 2.5 | 2.5 | 2.5 | 2.1 |
| date06 | 8 | 21.5 | 11.5 | 7.0 | 7.0 | 2.5 | 2.1 |
| mixed | 0 | 5.5 | 4.4 | 3.2 | 3.1 | 3.2 | 2.5 |
| mixed | 8 | 9.3 | 9.2 | 8.2 | 5.4 | 3.2 | 2.5 |
| kang_dl | 0 | 4.4 | 4.1 | 3.3 | 3.3 | 3.3 | 2.4 |
| kang_dl | 8 | 5.4 | 5.4 | 5.4 | 4.3 | 3.3 | 2.4 |
| kang_dh | 0 | 2.2 | 2.2 | 2.2 | 2.2 | 2.2 | 2.0 |
| kang_dh | 8 | 2.2 | 2.2 | 2.2 | 2.2 | 2.2 | 2.0 |

Yield Poisson tại mật độ mà TRIAD không phân vùng đạt khoảng 90 % tỉ lệ sửa (R = 2, K = 0):
date06 0.774 -> 0.996 (16 vùng); mixed 0.734 -> 0.966; kang_dl 0.730 -> 0.926; kang_dh 0.794 -> 0.832.

## Nhận xét

1. **Phân vùng có lợi rõ khi lỗi cell/cụm chiếm đa số**: date06 gấp 3.3 lần ở K = 0; mixed gấp 1.7 lần;
   kang_dl gấp 1.3 lần.
2. **Không có lợi khi lỗi đường chiếm đa số** (kang_dh): mọi phương án chính xác bằng nhau, vì giới hạn
   là số từ dự phòng cho word-line đứt.
3. **ECC có ngân sách** nâng mạnh khả năng chịu lỗi khi lỗi là cell (date06: 2.5 -> 7.0 với K = 8) và
   gần như không giúp gì với kang_dh.
4. Với K = 0, TRIAD không phân vùng trùng với BIRA 2D chính xác, đúng như lý thuyết.
5. Cột "kiểu EBISR" không đưa vào bảng: dưới cùng ngân sách K nó gần như luôn thất bại (n90 từ 0.1 đến
   3.0), vì EBISR nguyên bản không có ngân sách. So sánh công bằng với EBISR phải ở K không giới hạn và
   kèm số từ tiêu ECC (đã có ở `docs/02_g2_report.md`).

## Giới hạn

- Spare được coi là không lỗi trong Monte Carlo này (mô hình sát phần cứng thì có xét).
- Chưa có normalized repair rate theo định nghĩa gốc (so với "sửa được về nguyên tắc" của từng kiến
  trúc); cột `nrr` trong CSV lấy TRIAD không phân vùng làm mốc.
