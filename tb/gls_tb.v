`timescale 1ns/1ps
// Gate-level simulation top: the routed triad_bisr_top netlist with the fault-injectable macro
// model.  Same port surface as top_tb but no parameters — the netlist is fully elaborated.
module gls_tb (
    input  wire        rst_n,
    input  wire        bist_start,
    input  wire [4:0]  cfg_k,
    output wire        bist_busy,
    output wire        bist_done,
    output wire        bist_pass,
    output wire [1:0]  stat_fail_code,
    output wire [5:0]  stat_ecc_words,
    output wire [2:0]  stat_spare_words,
    input  wire        req_en,
    input  wire        req_we,
    input  wire [7:0]  req_addr,
    input  wire [23:0] req_wdata,
    output wire [23:0] rdata,
    output wire        rvalid,
    output wire        rd_ce,
    output wire        rd_ue,
    input  wire        sig_shift,
    input  wire        sig_in,
    output wire        sig_out,
    output reg         clk
);
    initial clk = 1'b0;
    always #20 clk = ~clk;

    triad_bisr_top dut (
        .clk(clk), .rst_n(rst_n), .bist_start(bist_start), .cfg_k(cfg_k),
        .bist_busy(bist_busy), .bist_done(bist_done), .bist_pass(bist_pass),
        .stat_fail_code(stat_fail_code), .stat_ecc_words(stat_ecc_words),
        .stat_spare_words(stat_spare_words),
        .req_en(req_en), .req_we(req_we), .req_addr(req_addr), .req_wdata(req_wdata),
        .rdata(rdata), .rvalid(rvalid), .rd_ce(rd_ce), .rd_ue(rd_ue),
        .sig_shift(sig_shift), .sig_in(sig_in), .sig_out(sig_out));
endmodule
