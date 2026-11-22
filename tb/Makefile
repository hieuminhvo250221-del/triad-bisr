# cocotb + Icarus.  Usage (inside WSL, after `source tools/env.sh`):
#   make -C tb TOPLEVEL=dp_tb_top MODULE=test_datapath SRC="../rtl/ecc30_24.v ../rtl/triad_datapath.v dp_tb_top.v"
SIM             ?= icarus
# The OSS CAD Suite vvp loads its own Python runtime, which breaks cocotb in the venv: use the apt Icarus (11.0).
ICARUS_BIN_DIR  ?= /usr/bin
TOPLEVEL_LANG   ?= verilog
TOPLEVEL        ?= dp_tb_top
MODULE          ?= test_datapath
SRC             ?=
VERILOG_SOURCES  = $(abspath sram_fault_model.v) $(abspath $(SRC))
export PYTHONPATH := $(abspath ../model):$(PYTHONPATH)
COMPILE_ARGS    += $(EXTRA_COMPILE_ARGS)
SIM_BUILD       ?= $(abspath ../build/sim/$(TOPLEVEL))
COCOTB_RESULTS_FILE ?= $(SIM_BUILD)/results.xml
include $(shell cocotb-config --makefiles)/Makefile.sim
