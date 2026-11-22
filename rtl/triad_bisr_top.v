`timescale 1ns/1ps
// TRIAD-P: 256 x 24-bit self-testing, self-repairing memory built around the sky130 OpenRAM macro
// sky130_sram_1kbyte_1rw1r_32x256_8 (see docs/05_architecture.md).
module triad_bisr_top #(
    parameter PBITS = 4,   // 2**PBITS address partitions for the spare-column steering table
    parameter R     = 2,   // spare words
    parameter NBG   = 6    // March data backgrounds (1..6)
) (
    input  wire        clk,
    input  wire        rst_n,
    // self-test / self-repair
    input  wire        bist_start,
    input  wire [4:0]  cfg_k,            // ECC budget: words allowed to rely on ECC for a hard fault
    output wire        bist_busy,
    output wire        bist_done,
    output wire        bist_pass,
    output wire [1:0]  stat_fail_code,
    output wire [5:0]  stat_ecc_words,
    output wire [2:0]  stat_spare_words,
    // user port (ignored while bist_busy); read data two clock edges after the request
    input  wire        req_en,
    input  wire        req_we,
    input  wire [7:0]  req_addr,
    input  wire [23:0] req_wdata,
    output wire [23:0] rdata,
    output wire        rvalid,
    output wire        rd_ce,
    output wire        rd_ue
);
    localparam WBITS = 8 - PBITS;

    // March engine
    wire        m_start, m_raw, m_busy, m_done, m_fail;
    wire [7:0]  m_base;
    wire [8:0]  m_len;
    wire        t_en, t_we;
    wire [7:0]  t_addr;
    wire [31:0] t_wdata;
    wire        f_valid;
    wire [7:0]  f_addr;
    wire [31:0] f_diff;
    // analyser / dynamic programme / configuration
    wire               en_clear, en_start, en_busy, en_done, c_multi, c_single;
    wire [2:0]         en_qsel, dp_rd_r, dp_rd_q;
    wire [6*(R+1)-1:0] e_flat;
    wire [5:0]         best0, best1, best_total, steer_sel0, steer_sel1;
    wire [6:0]         best_nm;
    wire [WBITS-1:0]   c_idx;
    wire               dp_init, dp_upd, cfg_clear, steer_we, spare_we;
    wire [PBITS-1:0]   dp_part;
    wire [7:0]         spare_addr;
    // datapath
    wire        d_rvalid;
    wire [31:0] rraw;
    wire        s_csb, s_web;
    wire [7:0]  s_addr;
    wire [31:0] s_din, s_dout, s_dout1;

    wire        d_en    = bist_busy ? t_en   : req_en;
    wire        d_we    = bist_busy ? t_we   : req_we;
    wire        d_raw   = bist_busy & m_raw;
    wire [7:0]  d_addr  = bist_busy ? t_addr : req_addr;
    wire [31:0] d_wdata = bist_busy ? t_wdata : {8'd0, req_wdata};

    assign rvalid           = d_rvalid & ~bist_busy;
    assign stat_ecc_words   = best_total;

    bisr_ctrl #(.PBITS(PBITS), .R(R)) u_ctrl (
        .clk(clk), .rst_n(rst_n), .start(bist_start), .cfg_k(cfg_k),
        .busy(bist_busy), .done(bist_done), .pass(bist_pass), .fail_code(stat_fail_code),
        .m_start(m_start), .m_base(m_base), .m_len(m_len), .m_raw(m_raw), .m_done(m_done), .m_fail(m_fail),
        .f_valid(f_valid),
        .en_clear(en_clear), .en_start(en_start), .en_qsel(en_qsel), .en_done(en_done), .e_flat(e_flat),
        .best0(best0), .best1(best1), .best_nm(best_nm), .c_idx(c_idx), .c_multi(c_multi), .c_single(c_single),
        .dp_init(dp_init), .dp_upd(dp_upd), .dp_part(dp_part), .best_total(best_total),
        .dp_rd_r(dp_rd_r), .dp_rd_q(dp_rd_q),
        .cfg_clear(cfg_clear), .steer_we(steer_we), .steer_sel0(steer_sel0), .steer_sel1(steer_sel1),
        .spare_we(spare_we), .spare_addr(spare_addr));

    mbist_march u_march (
        .clk(clk), .rst_n(rst_n), .start(m_start), .base(m_base), .len(m_len), .raw(m_raw), .nbg(NBG[2:0]),
        .busy(m_busy), .done(m_done), .fail(m_fail),
        .req_en(t_en), .req_we(t_we), .req_addr(t_addr), .req_wdata(t_wdata),
        .rdata(rdata), .rd_ue(rd_ue), .rraw(rraw),
        .f_valid(f_valid), .f_addr(f_addr), .f_diff(f_diff));

    alloc_enum #(.WBITS(WBITS), .R(R)) u_enum (
        .clk(clk), .rst_n(rst_n), .clear(en_clear),
        .f_valid(f_valid), .f_idx(f_addr[WBITS-1:0]), .f_diff(f_diff),
        .start(en_start), .q_sel(en_qsel), .busy(en_busy), .done(en_done), .e_flat(e_flat),
        .best0(best0), .best1(best1), .best_nm(best_nm),
        .c_idx(c_idx), .c_multi(c_multi), .c_single(c_single));

    alloc_dp #(.PBITS(PBITS), .R(R)) u_dp (
        .clk(clk), .rst_n(rst_n), .init(dp_init), .upd(dp_upd), .part(dp_part), .e_flat(e_flat),
        .best_total(best_total), .rd_part(dp_part), .rd_r(dp_rd_r), .rd_q(dp_rd_q));

    triad_datapath #(.PBITS(PBITS), .R(R)) u_dpath (
        .clk(clk), .rst_n(rst_n), .en(d_en), .we(d_we), .raw(d_raw), .addr(d_addr), .wdata(d_wdata),
        .rvalid(d_rvalid), .rdata(rdata), .rd_ce(rd_ce), .rd_ue(rd_ue), .rraw(rraw),
        .cfg_clear(cfg_clear), .steer_we(steer_we), .steer_part(dp_part),
        .steer_sel0(steer_sel0), .steer_sel1(steer_sel1),
        .spare_we(spare_we), .spare_addr(spare_addr), .spare_count(stat_spare_words),
        .m_csb(s_csb), .m_web(s_web), .m_addr(s_addr), .m_din(s_din), .m_dout(s_dout));

    sky130_sram_1kbyte_1rw1r_32x256_8 u_sram (
        .clk0(clk), .csb0(s_csb), .web0(s_web), .wmask0(4'hF), .addr0(s_addr), .din0(s_din), .dout0(s_dout),
        .clk1(1'b0), .csb1(1'b1), .addr1(8'd0), .dout1(s_dout1));

    wire unused = &{1'b0, m_busy, en_busy, s_dout1, f_addr[7:WBITS]};
endmodule
