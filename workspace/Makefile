# Makefile
SIM ?= verilator
TOPLEVEL_LANG ?= verilog
VERILOG_SOURCES += $(PWD)/dut.v
TOPLEVEL = my_module
MODULE = testbench
EXTRA_ARGS += --trace --trace-structs --Wno-fatal
include $(shell cocotb-config --makefiles)/Makefile.sim
