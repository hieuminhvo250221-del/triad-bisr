# Nhật ký tiến độ

Cập nhật file này sau mỗi mốc. Mục mới nhất ở trên cùng.

## 2026-11-22 — Pha 1 (G1) và pha 2a (G2) xong lượt đầu

- Mô hình vàng Python (`model/triad/`) khớp vét cạn 100 % trên 9 000 bản đồ lỗi; 9 test đạt; kiểm tra
  đột biến xác nhận test đủ nhạy.
- G1: **thu hẹp** phát biểu đóng góp (đã có RA tối ưu spare + ECC phía ATE: Lv et al., TC 2021).
- G2: giữ kiến trúc, đổi trọng tâm. Chính xác so với tham lam: tối đa +0.40 điểm % yield. Công thức
  đồng thời so với ECC-trước + mua lại: +1 đến +28 điểm % khi có lỗi đường. Xem `docs/02_g2_report.md`.
- Phát biểu đóng góp mới và thay đổi các pha sau: mục 8 của `docs/00_plan.md`.
- Còn nợ: toàn văn Lv 2021 / Lu 2016 / Han 2021; chạy bộ nhớ lớn (4096x39) với nhiều mẫu hơn;
  mô hình spare có lỗi; số đo SER thực cho sky130.

### Việc tiếp theo
1. Pha 3: đặc tả kiến trúc + sơ đồ (giao diện macro, định thời đọc nửa chu kỳ, CSR, FSM).
2. Pha 4: RTL (ecc, mbist, fault_collect, bộ giải chính xác và bộ tham lam, bisr_datapath, top).

## 2026-11-22 — Pha 0 hoàn tất (môi trường)

- Kế hoạch được duyệt (`docs/00_plan.md`): BIRA 3 tài nguyên + ECC, macro OpenRAM sky130 thật, làm mới
  hoàn toàn (không dùng dữ liệu q22013/D1b cũ), paper IEEE tiếng Anh, slide PowerPoint tiếng Anh,
  đích nộp: đồ án tốt nghiệp + hội nghị. Bốn bổ sung cho hướng NCKH đã ghi ở mục 5 của kế hoạch.
- Đã cài ở mức người dùng và chạy thử đạt: OpenLane 1.0.2 (Docker), OSS CAD Suite (Yosys 0.71,
  Icarus 14, Verilator 5.055, SBY), Magic/Netgen/ngspice native, ORFS 26Q2 + OpenROAD 26Q2,
  Tectonic (LaTeX), venv Python. Chi tiết và kết quả chạy thử: `docs/env/ENVIRONMENT.md`.
- OpenLane cũ của người dùng mở lại được bằng `openlane-mount`; `~/OpenLane` không bị sửa.
- Sự cố trong pha này (đã xử lý):
  1. Một heredoc ghi `AGENTS.md` kết thúc sớm, phần còn lại của tài liệu bị chạy như lệnh shell trên
     Windows. Hậu quả: chạy lại smoke test OpenLane trong WSL (vô hại) và bắt đầu tải một file 751 MB
     vào `C:\Users\Admin\work` (thư mục do chính lần chạy nhầm tạo ra; đã xoá). Không thấy thay đổi nào khác.
  2. Image OpenLane biến mất một lần sau khi WSL khởi động lại, chưa rõ nguyên nhân; đã pull lại và
     từ đó ổn định.
- Chưa làm: thử các giao diện đồ hoạ.

### Việc tiếp theo
1. Pha 2a (cổng G2, làm trước RTL): mô hình vàng Python + Monte Carlo so TRIAD với ECC-trước/EBISR,
   2D chính xác, ESP; cả kích thước lớn; quy đổi FIT.
2. Pha 1 (cổng G1): tổng quan tài liệu ~30 công trình, đọc toàn văn IEEE Access 2021 và EBISR 2016.
