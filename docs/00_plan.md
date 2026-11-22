# Kế hoạch dự án TRIAD-BISR (đã duyệt ngày 2026-11-22)

**Đề tài:** Nghiên cứu và thiết kế kiến trúc bộ nhớ SRAM nhúng có tích hợp kỹ thuật kiểm tra – tự sửa
lỗi tự động (MBIST–BISR) dựa trên thuật toán phân bổ tài nguyên dự phòng. Công nghệ ASIC, sky130,
toàn bộ bằng công cụ mã nguồn mở. Sản phẩm cuối: thiết kế RTL-to-GDS, paper IEEE (tiếng Anh, LaTeX),
slide PowerPoint (tiếng Anh). Đích nộp: đồ án tốt nghiệp + bài hội nghị.

**Quy tắc của đề tài:** phải có tính mới hoặc đóng góp cụ thể; nếu tính mới thuật toán không đứng
vững thì đóng góp bằng đánh đổi PPA có số liệu.

## 1. Những gì KHÔNG được tuyên bố là mới

| Nội dung | Công trình đã có |
|---|---|
| MBIST + BIRA 2D chính xác + BISR mã nguồn mở trên sky130/OpenRAM | autoMBIST (2026, GitHub ranaumarnadeem/autoMBIST) |
| BIRA 2D tối ưu | CRESTA (ITC 2000), SPOT (TVLSI 2025) |
| Thu hồi CAM động khi thu lỗi | Dynamic BIRA (TVLSI 2019) |
| Kết hợp ECC + BISR | EBISR (Lu, TVLSI 2016: ECC trước, spare sau, heuristic ESP); Siemens (ETS 2024); ECC-aware RA phía ATE cho DRAM (Han, IEEE Access 2021) |
| Sửa gần đúng theo mức quan trọng bit | MIMS (DAC 2011), ISQED 2017 |

## 2. Đóng góp dự kiến (kiến trúc tên tạm TRIAD-BIRA)

- **C1 – Phân bổ đồng thời 3 tài nguyên trên chip:** hàng dự phòng (R), cột dự phòng (S) và ECC
  SEC-DED, với ngân sách ECC `K` lập trình được (số từ tối đa được phép "tiêu" ECC cho lỗi cứng).
  Mục tiêu theo thứ tự từ điển: sửa được -> ít từ tiêu ECC nhất -> ít spare nhất (chế độ
  RELIABILITY-FIRST), hoặc sửa được với E <= K -> ít spare nhất (chế độ SPARE-SAVING).
  *Rủi ro trùng:* IEEE Access 2021 cũng nhắm dùng ECC tiết kiệm, nhưng ở phía ATE, cho DRAM, không
  chính xác-có-chứng-minh và không có ngân sách lập trình được.
- **C2 – Chặn trên kích thước CAM:** sau must-repair có ECC, số từ lỗi cần lưu <= `R + S(R+K) + K`;
  vượt quá => chắc chắn không sửa được => dừng sớm.
- **C3 – Bộ giải chính xác nối tiếp:** tìm kiếm rẽ 3 nhánh (hàng / cột lỗi thứ nhất / cột lỗi thứ
  hai của một "từ xung đột"), sâu tối đa `R+S`, tại mỗi lá dùng spare thừa "mua lại" ECC theo kiểu
  tham lam (tối ưu vì các tập phủ của cột rời nhau). Có chứng minh tính tối ưu.
- **C4 – Hiện thực RTL-to-GDS trên sky130 với macro OpenRAM thật** + so sánh với BIRA 2D chính xác
  (`K=0`), ECC-trước kiểu EBISR, ESP.
- **Đánh đổi PPA:** diện tích, công suất, trễ đường đọc tăng (ECC, CAM, remap); đổi lại yield cao hơn
  với cùng số spare và mức suy giảm chống soft-error bị chặn bởi `K`.

Phần mạnh nhất: C2, C3. Phần yếu nhất: C1 (trùng ý tưởng một phần), C4 (autoMBIST đã có luồng mở).

## 3. Mô hình bài toán

Bộ nhớ N từ x W bit vật lý (W = k dữ liệu + c kiểm tra + S cột dự phòng). Lỗi là cặp (từ, bit).
Chọn tập hàng X (|X| <= R), tập cột Y (|Y| <= S) sao cho mỗi từ không thuộc X còn <= 1 bit lỗi
ngoài Y, và số từ còn đúng 1 bit lỗi ngoài Y (E) <= K.

- Must-repair cột: cột có số từ lỗi > R_còn + K  => bắt buộc thuộc Y.
- Must-repair hàng: từ có số bit lỗi ngoài cột bắt buộc > S_còn + [K>0] => bắt buộc thuộc X.
- Rẽ nhánh: với từ có >= 2 bit lỗi chưa phủ b1, b2: mọi lời giải phải chứa hàng đó, hoặc cột b1,
  hoặc cột b2.
- Độ tin cậy: từ tiêu ECC cho lỗi cứng sẽ thành lỗi không sửa được khi gặp 1 soft error;
  FIT_DUE ~ E x W x lambda_bit, nên E là đại lượng cần tối thiểu và K là chặn trên.

## 4. Kiến trúc

```
            +---------------- triad_bisr_top -----------------+
 CSR/ctrl ->| bist_fsm: test -> analyze -> apply -> verify    |
            |   mbist_ctrl (March C-/X/MATS+, data background)|
            |        | vector lỗi 32 bit                      |
            |   fault_collect (đếm cột, must-repair, CAM)     |
            |   triad_solver  (tìm kiếm chính xác + mua lại)  |
            |   repair_regs   (chữ ký sửa, xuất/nhập qua CSR) |
 user  <--->| bisr_datapath: CAM địa chỉ -> spare word (FF)   |
 port       |   lái cột <-> ecc_enc/dec SEC-DED(30,24)        |
            |        |                                        |
            |   sky130_sram_1kbyte_1rw1r_32x256_8 (macro 6T)  |
            +-------------------------------------------------+
```

- Cấu hình chính: 256 từ x 32 bit vật lý = 24 dữ liệu + 6 kiểm tra (Hsiao SEC-DED) + 2 cột dự phòng;
  R = 2 hàng dự phòng bằng thanh ghi; K tối đa 8. Chốt lại ở pha 3 sau khảo sát nhanh.
- Sửa mềm lúc power-on (PDK mở không có eFuse); chữ ký sửa xuất/nhập qua CSR.
- RTL: Verilog-2005.
- Lưu ý macro: dout đổi ở sườn xuống của clk (lib: falling_edge) => đường đọc -> ECC chỉ có nửa chu kỳ
  nếu không pipeline; `.lib` là mô hình giải tích, chỉ có góc TT.

## 5. Các pha và cổng

| Pha | Nội dung | Sản phẩm / tiêu chí |
|---|---|---|
| 0 | Môi trường | Xong, xem `docs/env/ENVIRONMENT.md` |
| 1 | Tổng quan tài liệu | Bảng ~30 công trình, ma trận tuyên bố C1–C4. **Cổng G1:** giữ / thu hẹp / chuyển PPA |
| 2 | Thuật toán + mô hình vàng Python | Mô hình lỗi, TRIAD, vét cạn, baseline ESP/LRM/2D-exact/EBISR; Monte Carlo. **Cổng G2 (go/no-go, TRƯỚC khi viết RTL):** TRIAD có hơn rõ ECC-trước/EBISR về yield hoặc số từ tiêu ECC không? Nếu không -> trọng tâm PPA |
| 3 | Đặc tả kiến trúc + sơ đồ | `docs/arch/` |
| 4 | RTL | ecc, mbist, fault_collect, triad_solver, bisr_datapath, top; RTL baseline ESP |
| 5 | Kiểm chứng | cocotb + Icarus (hướng); Verilator hồi quy >= 10^4 bản đồ lỗi so với mô hình vàng; lint; GLS |
| 6 | ASIC OpenLane 1 | GDS; DRC định tuyến = 0; Magic DRC/Netgen LVS (macro hộp đen); antenna; STA đa góc. ORFS làm luồng đối chứng |
| 7 | Thí nghiệm PPA | Biến thể: wrapper trần / MBIST / BISR 2D / chỉ ECC / TRIAD; pipeline; quét (R,S,K) |
| 8 | Paper IEEE + slide PowerPoint (tiếng Anh) | Hình sinh bằng script từ dữ liệu thật |

**Bốn bổ sung đã thống nhất (để đủ sức nặng NCKH):**
1. Monte Carlo Python chạy trước RTL (cổng G2).
2. Đánh giá thuật toán ở kích thước lớn hơn 256x32 (vd. 1024x1024 theo chuẩn so sánh trong tài liệu), chỉ bằng mô hình Python.
3. Cài lại trung thực ít nhất một baseline đã công bố (EBISR), không chỉ so với `K=0` của chính mình.
4. Định lượng độ tin cậy bằng FIT theo số từ tiêu ECC.

## 6. Thí nghiệm

- E1 Tỉ lệ sửa (và tỉ lệ sửa chuẩn hoá) theo số lỗi, theo hỗn hợp loại lỗi, các cấu hình (R,S,K).
- E2 Yield theo mật độ khuyết tật (Poisson, nhị thức âm); số spare tiết kiệm ở cùng yield.
- E3 Độ tin cậy: phân bố E; FIT_DUE; RELIABILITY-FIRST so với ECC-trước.
- E4 RTL so với mô hình vàng: >= 10^4 bản đồ lỗi; độ phủ March theo mô hình lỗi.
- E5 PPA sau route: phân rã diện tích, fmax, công suất, số chu kỳ phân tích.
- E6 Quy mô: diện tích khối BIRA theo (R,S,K,N,W) (tổng hợp).

## 7. Giới hạn sẽ ghi rõ trong paper

- `.lib` macro OpenRAM là mô hình giải tích, chỉ có góc TT -> fmax chủ yếu phản ánh logic wrapper.
- DRC/LVS coi macro là IP đã kiểm chứng (hộp đen).
- Từ 24 bit để vừa khít một macro; 32 bit dữ liệu cần hai macro (phần mở rộng).
- Không có silicon; sửa mềm thay cho eFuse.

## 8. Kết quả cổng G1 và G2 (2026-11-22) — phát biểu đóng góp đã chỉnh

Chi tiết: `docs/01_related_work.md`, `docs/02_g2_report.md`.

- **G1: thu hẹp.** Lv et al. (IEEE Trans. Computers 2021) đã có RA tối ưu cho spare + in-memory ECC
  (phía ATE, DRAM, không ngân sách); Han et al. (IEEE Access 2021) đã nhắm dùng ECC tiết kiệm. Vì vậy
  **không** viết "first joint/optimal ECC + redundancy analysis".
- **G2: giữ kiến trúc, đổi trọng tâm.** Tìm kiếm chính xác chỉ hơn heuristic tham lam cùng công thức
  tối đa 0.40 điểm % yield. Lợi ích đo được nằm ở công thức đồng thời (+1 đến +28 điểm % so với
  ECC-trước + mua lại khi có lỗi đường), ở bước mua lại (ít hơn 55–100 % từ tiêu ECC so với kiểu EBISR)
  và ở ngân sách K.

Phát biểu đóng góp dùng từ nay:

1. Bộ phân bổ **tích hợp trên chip** cho ba tài nguyên (từ dự phòng, cột dự phòng, ECC) **dưới ngân
   sách độ tin cậy K lập trình được**, có bước mua lại để tối thiểu số từ tiêu ECC.
2. Chặn trên **chặt** cho bộ lưu lỗi, `R + S(R+K) + K`, và must-repair có ECC cho cả từ lẫn cột.
3. Bộ giải chính xác nối tiếp có chặn 3^(R+S) nút, kèm **so sánh chi phí phần cứng với bộ tham lam**:
   trả lời câu hỏi "bảo đảm tối ưu tốn bao nhiêu diện tích và thời gian".
4. Hiện thực RTL-to-GDS nguồn mở trên sky130 với macro OpenRAM thật; đường cong đánh đổi
   yield – số từ tiêu ECC (FIT) – PPA theo K.

Thay đổi trong các pha sau:
- Pha 4: viết thêm RTL bộ tham lam (cùng giao diện) để so PPA với bộ chính xác.
- Pha 7: thêm thí nghiệm "chính xác so với tham lam" (diện tích, số chu kỳ phân tích, fmax).
- Pha 1 còn nợ: đọc toàn văn Lv 2021, Lu 2016, Han 2021 để so cấu trúc tìm kiếm và cài lại EBISR đúng bản gốc.
