# Môi trường công cụ (pha 0, hoàn tất 2026-11-22)

Máy chạy: WSL2 `Ubuntu-22.04` (Ubuntu 22.04.5, kernel 6.6.87.2), 12 luồng, 11 GB RAM, user `hieu`.
Đĩa ảo WSL nằm trên `C:` (còn khoảng 29 GB trống trên C:), nên tổng dung lượng cài thêm được giữ ở mức ~6 GB.
Mọi thứ cài ở mức người dùng trong `~/work/eda-tools` và Docker; không dùng `sudo`, không sửa hệ thống.

## 1. Công cụ

| Công cụ | Phiên bản | Vị trí / cách gọi | Nguồn cài | Dùng cho |
|---|---|---|---|---|
| OpenLane 1 | 1.0.2 (`ff5509f`) | `ol-flow`, `ol-exec`, `ol-shell`, `openlane-mount` | Docker image `ghcr.io/the-openroad-project/openlane:ff5509f65b17bfa4068d5336495ab1718987ff69-amd64`, digest `sha256:832662c878405772fdb759a11daf21c32fd50072be6b6f4305ca377b4650779a`, 1.4 GB | Luồng RTL-to-GDS chính, sign-off |
| – Yosys (trong image) | 0.30+48 | `ol-exec yosys` | | Tổng hợp trong OpenLane |
| – OpenROAD (trong image) | `41a51ea` | `ol-exec openroad` | | P&R trong OpenLane |
| – Magic (trong image) | 8.3.413 | `ol-exec magic` | | DRC, trích xuất, GDS (sign-off) |
| – Netgen (trong image) | 1.5.255 | `ol-exec netgen` | | LVS (sign-off) |
| – KLayout / Verilator / OpenSTA (trong image) | 0.28.2 / 5.009 / 2.4.0 | `ol-exec ...` | | XOR, lint, STA |
| OSS CAD Suite | 2026-11-14 | `~/work/eda-tools/oss-cad-suite` (2.5 GB) | GitHub YosysHQ, tgz sha256 `25d1960bc0f002c43b3579423c4e622bcffed49b7bb8b1f02df6426b1bdd2f26` | |
| – Yosys | 0.71+34 | `yosys` | | Tổng hợp cho ORFS, khảo sát diện tích |
| – Icarus Verilog | 14.0 (devel) | `iverilog`, `vvp` | | Mô phỏng (cocotb) |
| – Verilator | 5.055 | `verilator` | | Lint, hồi quy tốc độ cao |
| – SymbiYosys | 0.70 | `sby` | | Kiểm chứng hình thức (tuỳ chọn) |
| OpenROAD (native) | 26Q2-1164-g08f67ee5ec | `openroad`, `openroad -gui` | có sẵn từ trước (`~/.local/opt`) | ORFS, STA, công suất |
| OpenSTA (native) | 3.1.0 | `sta` (wrapper `tools/bin/sta`) | đi kèm OpenROAD 26Q2 | STA độc lập |
| OpenROAD-flow-scripts | tag `26Q2` (`036d106`), sparse 525 MB | `$FLOW_HOME` = `~/work/eda-tools/OpenROAD-flow-scripts/flow` | git clone mới (bản cũ `~/OpenROAD-flow-scripts` giữ nguyên) | Luồng P&R đối chứng, quét nhanh |
| Magic (native) | 8.3.678 | `magic` | micromamba, conda-forge | Xem layout, thao tác tương tác |
| Netgen LVS (native) | 1.5.272 | `netgen` | micromamba, litex-hub | LVS tương tác |
| ngspice | 41 | `ngspice` | micromamba, conda-forge | Mô phỏng SPICE (bitcell, đường tới hạn) |
| micromamba | 2.10.0 | `~/work/eda-tools/bin/micromamba` | GitHub, sha256 khớp file công bố `701f39c0...e8bd` | Quản lý 2 env trên |
| Tectonic (LaTeX) | 0.17.0+20260731 | `tectonic -X compile x.tex` | GitHub, sha256 `9684093ea8a091be6bc2105cbb74ee7055798f2adc1b0ee3654cefa66d0d3834` | Paper IEEEtran |
| Python venv | 3.10.12 | `~/work/eda-tools/venv` | `requirements.txt` (ghim cứng) | Mô hình, kiểm chứng, hình, slide |
| KLayout (native) | 0.30.7 | `klayout` | có sẵn (apt) | Xem GDS, xuất ảnh layout |
| PDK sky130A/B | open_pdks `0fe599b` | `~/.ciel` | có sẵn (ciel) | Khớp đúng phiên bản OpenLane 1.0.2 ghim |
| GTKWave, Graphviz, Pandoc | | | có sẵn | Sóng, sơ đồ, chuyển định dạng |

Gói Python: numpy 2.2.6, scipy 1.15.3, matplotlib 3.10.9, pandas 2.3.3, pytest 9.2.0, cocotb 1.9.2,
python-pptx 1.0.2, PyYAML 6.0.3 (PyYAML là yêu cầu của script ORFS). Khoá đầy đủ: `results/env/requirements.lock`.

Mọi phiên bản cài mới đều đã phát hành ít nhất 7 ngày trước ngày cài.

## 2. Kết quả chạy thử

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| OpenLane 1, design `spm` RTL→GDS | `tools/setup/90_smoke_openlane.sh` | Hoàn tất 1 phút 14 giây; vi phạm định tuyến 0, Magic DRC 0, LVS 0 lỗi, antenna 0; có `spm.gds` |
| Mở lại OpenLane như trước | `openlane-mount` (= `make mount`) | Vào được container, prompt `OpenLane Container (ff5509f):/openlane$` |
| ORFS native, `gcd` sky130hd | `tools/setup/92_smoke_orfs.sh` | Chạy hết tổng hợp → route → RCX → báo cáo, có `6_final.gds`. Ví dụ gốc đặt clock 1.1 ns nên slack setup −1.68 ns: đây là đặc điểm của ví dụ, không phải lỗi công cụ |
| LaTeX IEEEtran + TikZ + algorithm + siunitx | `tools/setup/91_smoke_latex.sh` | Ra `smoke.pdf` |
| Magic native đọc tech sky130A | | `TECH sky130A version 1.0.493-0-g0fe599b` |
| ngspice, netgen native | | In đúng phiên bản |

Chưa thử: các giao diện đồ hoạ (`openroad -gui`, `klayout`, `magic` có cửa sổ) vì sẽ bật cửa sổ trên
màn hình; WSLg có sẵn (`DISPLAY=:0`).

## 3. Mở lại OpenLane bằng tay

```bash
wsl -d Ubuntu-22.04
source ~/work/triad_bisr/tools/env.sh
openlane-mount            # tương đương: cd ~/OpenLane && make mount OPENLANE_IMAGE_NAME=$OPENLANE_IMAGE_NAME
```

Lý do trước đây không mở được: image đã bị xoá, và nhánh `my_openlane_work` của `~/OpenLane` khiến
Makefile tìm tag `my_openlane_work-dev` không tồn tại. Cách trên truyền thẳng tag gốc; không sửa file
nào trong `~/OpenLane`.

## 4. Cài lại từ đầu

Chạy trong WSL, từ `~/work/triad_bisr`: `tools/setup/01_...06_*.sh` theo thứ tự, rồi `90/91/92` để kiểm tra.

## 5. Ghi chú và sự cố

- **Image OpenLane biến mất một lần.** Sau lần pull đầu, image dùng tốt khoảng 10 phút, rồi sau một
  lần WSL tự tắt/bật lại thì Docker báo không có image và tự pull lại. Chưa tìm ra nguyên nhân: không có
  cron/timer dọn Docker, nhật ký Docker không ghi lệnh xoá, và từ đó image tồn tại qua nhiều lần khởi
  động lại. `ol-exec` tự pull lại nếu thiếu (tốn ~445 MB tải).
- **WSL tự tắt** khoảng 15 giây sau khi không còn tiến trình `wsl.exe`; Docker dừng theo. Job dài phải
  chạy trong một lệnh `wsl` còn sống.
- **Dung lượng:** `~/work/eda-tools` 3.9 GB (sau khi xoá file tải về của OSS CAD Suite), image Docker 1.4 GB.
- **Không đụng:** `~/OpenLane`, `~/OpenROAD-flow-scripts`, `~/sram_openroad_lab_*`, `/var/tmp/*`, `~/.ciel`.
