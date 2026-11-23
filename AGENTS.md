# AGENTS.md — TRIAD-BISR (MBIST + BIRA + BISR for sky130 OpenRAM SRAM)

Read `docs/00_plan.md` (approved plan, contribution claims, gates) and `docs/STATUS.md` (progress log)
first.  Update `docs/STATUS.md` after every milestone.

## Where things run

- The repo lives on Windows: `D:\MBIST-BISR-BIRA SRAM ASIC PROJECT` (path has spaces, slow `/mnt/d`).
  **Never run EDA tools there.**  Edit files here; this is the git repository (remote: github.com/hieuminhvo250221-del/triad-bisr, public).
- All tools run in WSL (`Ubuntu-22.04`, user `hieu`) on a mirror: `~/work/triad_bisr`.
  Generated files go to `~/work/triad_bisr/build/` (never synced back automatically).
  Curated artifacts for the repo: put them in `build/export/`, then run `tools/sync_results.sh`
  (copies into `results/`).
- User-level tools: `~/work/eda-tools/` (see `docs/env/ENVIRONMENT.md`).  `sudo` needs a password: do not use it.

## Running commands (from Git Bash on Windows)

```bash
# sync repo -> WSL mirror, then run a script there with the environment loaded
tools/wsl.sh <<'EOS'
pytest -q model
EOS

# or by hand
wsl -- bash -l -s <<'EOF'
bash "/mnt/d/MBIST-BISR-BIRA SRAM ASIC PROJECT/tools/sync_to_wsl.sh"
cd ~/work/triad_bisr && source tools/env.sh
...
EOF

# run a script file that already exists in the mirror
MSYS_NO_PATHCONV=1 wsl -- bash -l /home/hieu/work/triad_bisr/tools/setup/90_smoke_openlane.sh
```

Pitfalls that already cost time:
- `wsl -- bash -lc '...$var...'` is parsed twice (variables vanish).  Feed the script on stdin instead.
- Git Bash rewrites arguments that look like `/home/...` into `C:/Program Files/Git/home/...`;
  prefix the command with `MSYS_NO_PATHCONV=1`.
- Inside a stdin-fed script, anything that reads stdin (docker run -i, openroad, sta, tclsh, magic,
  ngspice, ssh) swallows the rest of the script: always add `</dev/null`.
- Interactive PTY sessions are not available from this Windows shell; emulate a TTY inside WSL with
  `script -qec "<cmd>" /dev/null` when a tool insists on one.
- When writing a file with a heredoc, use a delimiter that cannot occur in the content
  (e.g. `<<'__FILE_END__'`).  A Markdown file that itself shows `EOF` once ended the heredoc early
  and the rest of the document was executed as shell commands.
- In heredocs sent through this shell, a doubled backslash collapses to one even with a quoted
  delimiter (LaTeX `\\`, escaped regexes).  Write such files with the file-writing tool or
  build the backslashes in Python (`chr(92)`).
- The WSL distro shuts down about 15 s after the last `wsl.exe` exits (Docker stops with it), so a
  long job must stay attached to a running `wsl` command.

## Do not touch

`~/OpenLane` (user's OpenLane 1 checkout), `~/OpenROAD-flow-scripts` (old partial copy),
`~/sram_openroad_lab_*`, `/var/tmp/*` (sealed data of an earlier project), `~/.ciel` (PDK), system packages.

## Tools (after `source tools/env.sh`)

| Purpose | Command | Notes |
|---|---|---|
| RTL-to-GDS sign-off flow | `ol-flow -design <abs dir> -tag <tag> -overwrite` | OpenLane 1.0.2 in Docker; Yosys 0.30, OpenROAD 41a51ea, Magic 8.3.413, Netgen 1.5.255, KLayout 0.28.2 |
| Any tool inside that image | `ol-exec <cmd>` / `ol-shell` | uses the image's own `/openlane` |
| Re-open the user's OpenLane | `openlane-mount` | = `make mount` in `~/OpenLane` with the right image tag |
| Second P&R flow (native) | `make -C $FLOW_HOME DESIGN_CONFIG=... WORK_HOME=...` | ORFS tag 26Q2 + OpenROAD 26Q2 + Yosys 0.71 |
| Simulation | `iverilog`/`vvp` 14.0, `verilator` 5.055, `cocotb` 1.9.2 | cocotb for directed tests, Verilator for mass regression |
| Synthesis experiments / formal | `yosys` 0.71, `sby` 0.70 | |
| STA / power | `sta` (bundled with OpenROAD 26Q2), `openroad` | |
| Layout viewing | `klayout` 0.30.7, `magic` 8.3.678, `openroad -gui` | GUI through WSLg |
| LVS (interactive) | `netgen` 1.5.272 | sign-off LVS runs inside OpenLane |
| SPICE | `ngspice` 41 | |
| LaTeX | `tectonic -X compile paper.tex` | IEEEtran works; packages fetched on demand |
| Python | venv `~/work/eda-tools/venv` (Python 3.10) | pins in `requirements.txt` |

PDK: `$PDK_ROOT/sky130A` = `~/.ciel/sky130A` (open_pdks 0fe599b).  SRAM macro views:
`$SRAM_MACRO_DIR/{gds,lef,lib,verilog,spice}`; the project uses `sky130_sram_1kbyte_1rw1r_32x256_8`.

## Setup / verification commands (run inside WSL, from the mirror)

```bash
tools/setup/01_openlane_image.sh   # docker pull (pinned tag)
tools/setup/02_oss_cad_suite.sh    # Yosys/Icarus/Verilator/SBY
tools/setup/03_micromamba_eda.sh   # ngspice, magic, netgen
tools/setup/04_orfs.sh             # sparse ORFS checkout
tools/setup/05_tectonic.sh         # LaTeX
tools/setup/06_python_venv.sh      # Python venv from requirements.txt
tools/setup/90_smoke_openlane.sh   # spm RTL->GDS, expects 0 DRC / 0 LVS errors
tools/setup/91_smoke_latex.sh      # IEEEtran PDF
tools/setup/92_smoke_orfs.sh       # gcd on sky130hd
```

## Project commands (inside WSL, from the mirror, after `source tools/env.sh`)

```bash
python -m pytest -q                         # golden models vs exhaustive search, theory checks (~90 s)
bash tb/regress.sh 24                       # cocotb: datapath unit tests + system tests for 3 configurations
bash tb/mutation_check.sh                   # 10 RTL mutants must all be caught by the directed system test
PYTHONPATH=model python -m triad.ecc rtl/ecc30_24.v   # regenerate the ECC RTL (copy it back to the repo)
cd model && python -m triad.mc --preset protocol --mixes kang_dl --trials 10000 --out ../build/proto/x.csv
```

- cocotb runs on the apt Icarus 11 (`ICARUS_BIN_DIR=/usr/bin` in `tb/Makefile`): the OSS CAD Suite `vvp`
  embeds its own Python and cannot load the venv.  Verilator 5 from OSS CAD Suite is used for lint.
- The RTL is checked against `model/triad/hwmodel.py` (same enumeration order, so even the chosen steering
  table and spare words must match), which is checked against the exact solvers and exhaustive search.
- Files written with the editor's file-writing tool arrive with CRLF; `tools/sync_to_wsl.sh` converts them.
- A shell command longer than about 8 kB is silently truncated: write big files in several pieces.

## Conventions

- RTL: Verilog-2005 (must pass Icarus, Verilator lint, Yosys 0.30 inside OpenLane).
- Python: 3.10, type hints, tests with pytest.  Random experiments take an explicit seed.
- New dependencies: exact version pins, published at least 7 days earlier; record them in
  `requirements.txt` / `docs/env/ENVIRONMENT.md`.
- Every number in the paper/slides must come from a script under version control and a file in `results/`.
- Honest reporting: never claim sign-off results that were not produced by a logged run.
- Git: commit at milestones, do not push.  Docs for the user are in Vietnamese; code, paper and slides in English.

## Website (site/)

- `site/` is an Astro static project (GitHub Pages, base `/triad-bisr/`, English at `/`, Vietnamese at `/vi/`).
- `python tools/site_data.py` regenerates `site/src/data/generated/*.json` from `results/` and copies the
  layout image into `site/public/assets/`; add `--check` to print the extracted ASIC values for review.
- Which run the site shows is controlled by the single line in `results/asic/CURRENT`.
- From `site/`: `npm run data`, `npm run dev` (preview), `npm run build` (data + astro check + build),
  `npm run screens` (Playwright screenshots into `site/.screens/`).
- Sections are MDX files under `site/src/content/sections/{en,vi}/`; frontmatter `order` sets numbering and
  nav, `id` must match across languages. Every number goes through generated JSON — see `site/README.md`.
- Deploy: `.github/workflows/pages.yml` on pushes to `main` touching `site/**`, `results/**`, or
  `tools/site_data.py`.
