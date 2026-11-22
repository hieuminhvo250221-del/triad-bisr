`timescale 1ns/1ps
// Unit-test harness: repair datapath + faulty macro model.
module dp_tb_top #(parameter PBITS = 4, parameter R = 2) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             en,
    input  wire             we,
    input  wire             raw,
    input  wire [7:0]       addr,
    input  wire [31:0]      wdata,
    output wire             rvalid,
    output wire [23:0]      rdata,
    output wire             rd_ce,
    output wire             rd_ue,
    output wire [31:0]      rraw,
    input  wire             cfg_clear,
    input  wire             steer_we,
    input  wire [PBITS-1:0] steer_part,
    input  wire [5:0]       steer_sel0,
    input  wire [5:0]       steer_sel1,
    input  wire             spare_we,
    input  wire [7:0]       spare_addr,
    output wire [2:0]       spare_count
);
    wire        m_csb, m_web;
    wire [7:0]  m_addr;
    wire [31:0] m_din, m_dout, m_dout1;

    triad_datapath #(.PBITS(PBITS), .R(R)) u_dp (
        .clk(clk), .rst_n(rst_n), .en(en), .we(we), .raw(raw), .addr(addr), .wdata(wdata),
        .rvalid(rvalid), .rdata(rdata), .rd_ce(rd_ce), .rd_ue(rd_ue), .rraw(rraw),
        .cfg_clear(cfg_clear), .steer_we(steer_we), .steer_part(steer_part),
        .steer_sel0(steer_sel0), .steer_sel1(steer_sel1),
        .spare_we(spare_we), .spare_addr(spare_addr), .spare_count(spare_count),
        .m_csb(m_csb), .m_web(m_web), .m_addr(m_addr), .m_din(m_din), .m_dout(m_dout));

    sky130_sram_1kbyte_1rw1r_32x256_8 u_ram (
        .clk0(clk), .csb0(m_csb), .web0(m_web), .wmask0(4'hF), .addr0(m_addr), .din0(m_din), .dout0(m_dout),
        .clk1(clk), .csb1(1'b1), .addr1(8'h00), .dout1(m_dout1));
endmodule
