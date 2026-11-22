# Pha 3 — Đặc tả kiến trúc TRIAD-P (bản 1, 2026-11-22)

Tên module và tín hiệu bằng tiếng Anh để khớp RTL. Cấu hình mặc định ghi trong ngoặc.

## 1. Tổng quan

```
                         +------------------------- triad_bisr_top --------------------------+
  cfg_k, bist_start ---->|  bisr_ctrl  (3 lượt: phân tích -> cấp phát -> kiểm tra)           |
  bist_done/pass/status<-|     |            |                |                |              |
                         |  mbist_march   win_bitmap     alloc_enum       alloc_dp           |
                         |  (March C-,    (WIN x 32 bit) (duyệt cặp cột,  (quy hoạch động    |
                         |   6 nền dữ      lỗi của một    đếm từ 1 lỗi /   chia R từ dự      |
                         |   liệu)         cửa sổ)        nhiều lỗi)       phòng, kiểm K)    |
                         |     | raw 32 bit                    | ghi bảng lái cột, từ dự phòng|
  req_en/we/addr/wdata ->|  triad_datapath: ecc_enc -> steer -> [macro] -> unsteer ->        |
  rdata/rvalid/ce/ue  <--|                  spare-word mux -> ecc_dec -> thanh ghi ra        |
                         |        sky130_sram_1kbyte_1rw1r_32x256_8 (cổng 0; cổng 1 tắt)     |
                         +-------------------------------------------------------------------+
```

- Bộ nhớ logic: 256 từ x 24 bit. Vật lý: 32 bit = 30 bit mã Hsiao SEC-DED (24 dữ liệu + 6 kiểm tra) ở
  bit [29:0] + 2 cột dự phòng ở bit [31:30].
- Tài nguyên sửa: R từ dự phòng bằng flip-flop (R = 2); S = 2 cột dự phòng, **lái theo phân vùng địa
  chỉ**: P = 2^PBITS phân vùng theo các bit địa chỉ cao (PBITS = 4, P = 16, mỗi phân vùng WIN = 16 từ);
  ECC với ngân sách K lập trình được (`cfg_k`, 0..31).
- Sửa mềm: chạy lại sau mỗi lần cấp nguồn. Chưa có xuất/nhập chữ ký sửa (để sau).

## 2. Thuật toán cấp phát trong phần cứng

Phần cứng **không** dùng CAM, must-repair hay tìm kiếm quay lui. Vì S = 2, nó dùng thuật toán duyệt tập
cột (Định lý 7, `docs/04_theory.md`) cho từng phân vùng và quy hoạch động giữa các phân vùng (Mệnh đề 8).
Bộ lưu lỗi là bitmap của **một** phân vùng (WIN x 32 = 512 flip-flop), không bao giờ tràn.

Với một phân vùng có bitmap `b[w][31:0]` và một phương án `(c0, c1)` (cột thay bằng cột dự phòng 0 và 1,
mỗi cái có thể là NONE):
- vector lỗi hiệu dụng của từ w: `v[j] = b[w][j]`, riêng `v[c0] = b[w][30]`, `v[c1] = b[w][31]`
  (lỗi của chính cột dự phòng được tính đúng theo cách này);
- từ có >= 2 bit lỗi trong `v` là từ xung đột (bắt buộc dùng từ dự phòng), có đúng 1 bit là từ đơn.
- Với q từ dự phòng cho phân vùng: khả thi khi `q >= n_multi`; `E = max(0, n_single - (q - n_multi))`.
- `e_p(q)` = E nhỏ nhất trên mọi phương án, q = 0..R. Chỉ duyệt các cột có lỗi trong phân vùng.

Quy hoạch động: `best[r]` = tổng E nhỏ nhất khi dùng tối đa r từ dự phòng; cập nhật
`best'[r] = min_q best[r-q] + e_p(q)` và lưu `choice[p][r]` (q đạt cực tiểu, ưu tiên q nhỏ).
Sửa được khi `best[R] <= K`.

Ba lượt:
1. **Phân tích**: với mỗi phân vùng p = 0..P-1: March C- riêng trên phân vùng (truy cập thô 32 bit) ->
   bitmap -> duyệt phương án -> `e_p(q)` -> cập nhật quy hoạch động.
2. **Cấp phát** (nếu sửa được): p = P-1..0: `q = choice[p][r_rem]`; March lại phân vùng để dựng lại
   bitmap; duyệt lại, giữ phương án tốt nhất cho q; ghi bảng lái cột của phân vùng; cấp từ dự phòng cho
   các từ xung đột rồi tới các từ đơn cho đủ q.
3. **Kiểm tra**: March C- trên toàn bộ nhớ qua đường dữ liệu đã sửa, có ECC. Sai dữ liệu sau sửa hoặc
   có lỗi không sửa được (`ue`) => thất bại.

Hệ quả cần ghi trong paper:
- Lượt 1-2 kiểm tra từng phân vùng riêng, nên lỗi ghép cặp (coupling) giữa hai phân vùng và lỗi bộ giải
  mã địa chỉ chỉ lộ ra ở lượt 3; khi đó kết luận là "không sửa được" chứ không được phân tích lại.
- Phần cứng tối thiểu (E, số từ dự phòng); không tối thiểu số đoạn cột dự phòng (dùng thêm không tốn gì).
- Từ dự phòng bằng flip-flop coi là không lỗi (thuộc phạm vi kiểm tra logic).

## 3. Giao diện `triad_bisr_top`

| Tín hiệu | Hướng | Ý nghĩa |
|---|---|---|
| `clk`, `rst_n` | vào | clock; reset bất đồng bộ mức thấp |
| `bist_start` | vào | xung 1 chu kỳ: chạy tự kiểm tra - tự sửa |
| `cfg_k[4:0]` | vào | ngân sách ECC K (số từ được phép dựa vào ECC cho lỗi cứng) |
| `bist_busy`, `bist_done` | ra | đang chạy / đã xong |
| `bist_pass` | ra | bộ nhớ dùng được (không lỗi hoặc đã sửa và kiểm tra đạt) |
| `stat_ecc_words[5:0]` | ra | E theo kế hoạch cấp phát |
| `stat_spare_words[2:0]` | ra | số từ dự phòng đã dùng |
| `stat_fail_code[1:0]` | ra | 0 đạt, 1 vượt ngân sách/không cấp phát được, 2 lượt kiểm tra thất bại |
| `req_en`, `req_we`, `req_addr[7:0]`, `req_wdata[23:0]` | vào | truy cập của người dùng (bị bỏ qua khi `bist_busy`) |
| `rdata[23:0]`, `rvalid` | ra | dữ liệu đọc, trễ 2 sườn clock sau yêu cầu |
| `rd_ce`, `rd_ue` | ra | ECC đã sửa 1 bit / phát hiện lỗi không sửa được (cùng lúc với `rvalid`) |

Định thời đọc: yêu cầu ở chu kỳ k được macro lấy mẫu tại sườn lên k+1; `dout0` của macro đổi sau sườn
xuống trong chu kỳ k+1 (theo `.lib`: `falling_edge`); đường lái ngược -> chọn từ dự phòng -> giải mã ECC
phải xong trong nửa chu kỳ còn lại; thanh ghi ra chốt tại sườn lên k+2.

## 4. Module

| Module | Chức năng | Trạng thái chính |
|---|---|---|
| `ecc30_24_enc/dec` | mã Hsiao (30,24), sinh từ `model/triad/ecc.py` | tổ hợp |
| `triad_datapath` | mã hoá, lái cột, từ dự phòng, giải mã, thanh ghi ra | bảng lái cột P x 2 x 6 bit; R x (1 + 8 + 30) bit |
| `mbist_march` | March C- trên dải địa chỉ [base, base+len), 6 nền dữ liệu; chế độ thô 32 bit hoặc logic 24 bit | bộ đếm địa chỉ, phần tử, nền |
| `win_bitmap` | bitmap lỗi một phân vùng, ghi kiểu OR | WIN x 32 bit |
| `alloc_enum` | duyệt (c0, c1), quét WIN từ, tính `e_p(q)`; ở lượt 2 trả phương án tốt nhất và danh sách từ cần thay | vài bộ đếm, R+1 thanh ghi |
| `alloc_dp` | `best[]`, `choice[][]`, quyết định sửa được | (R+1) x 6 bit; P x (R+1) x 2 bit |
| `bisr_ctrl` | máy trạng thái ba lượt | |
| `triad_bisr_top` | ghép macro, chọn BIST/người dùng | |

Tham số: `PBITS` (2..4), `R` (1..4). S = 2 và kích thước macro cố định trong bản này.

## 5. Ước lượng trước khi viết RTL (sẽ thay bằng số đo sau tổng hợp)

- Flip-flop: bitmap 512 + bảng lái cột 192 + từ dự phòng 78 + quy hoạch động khoảng 130 + MBIST và điều
  khiển khoảng 200 = khoảng 1 100.
- Thời gian tự sửa: mỗi lượt March một phân vùng 960 thao tác; duyệt phương án thường vài chục tới vài
  trăm chu kỳ mỗi phân vùng (tối đa 961 phương án x 16 từ); lượt kiểm tra 15 360 thao tác. Tổng cỡ
  50 000 - 100 000 chu kỳ khi ít lỗi.
- Macro chiếm 0.19 mm2; phần logic dự kiến chiếm tỉ lệ lớn so với macro vì bộ nhớ chỉ 8 kbit. Chi phí
  logic gần như không đổi khi bộ nhớ lớn lên (chỉ bảng lái cột tăng theo P), nên tỉ lệ này giảm nhanh
  với bộ nhớ lớn hơn; cần báo cáo cả hai.

## 6. Mô hình vàng sát phần cứng

`model/triad/hwmodel.py` mô phỏng đúng thuật toán mục 2 (kể cả lỗi của cột dự phòng). Kiểm chứng:
bằng `solve_partitioned` khi cột dự phòng không lỗi (cùng E và cùng kết luận), và bằng vét cạn khi cột
dự phòng có lỗi. RTL được so với mô hình này theo: sửa được/không, E, số từ dự phòng; lời giải của RTL
còn được kiểm bằng lượt 3 và bộ kiểm độc lập.
