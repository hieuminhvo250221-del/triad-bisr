`timescale 1ns/1ps
// Repair datapath around the 32-bit macro.
//   write: data[23:0] -> Hsiao (30,24) encoder -> bit steering -> macro din[31:0]
//   read : macro dout[31:0] -> inverse steering -> spare-word mux -> decoder -> output register
// Physical bits [29:0] hold the codeword, bits 30 and 31 are the two spare columns.  The steering
// select of each spare column is looked up per address partition (upper PBITS address bits).
// Read data is valid two clock edges after the request (the macro launches dout on the falling edge).
module triad_datapath #(
    parameter PBITS = 4,   // 2**PBITS address partitions (1..7)
    parameter R     = 2    // spare words (1..4)
) (
    input  wire             clk,
    input  wire             rst_n,
    // access request
    input  wire             en,
    input  wire             we,
    input  wire             raw,        // 1: bypass ECC, steering and spare words (BIST analysis)
    input  wire [7:0]       addr,
    input  wire [31:0]      wdata,      // raw: 32 physical bits, otherwise [23:0] = data
    // read result
    output reg              rvalid,
    output reg  [23:0]      rdata,
    output reg              rd_ce,
    output reg              rd_ue,
    output reg  [31:0]      rraw,
    // repair configuration
    input  wire             cfg_clear,
    input  wire             steer_we,
    input  wire [PBITS-1:0] steer_part,
    input  wire [5:0]       steer_sel0, // {valid, column} replaced by spare column 0
    input  wire [5:0]       steer_sel1, // {valid, column} replaced by spare column 1
    input  wire             spare_we,   // give the next free spare word to spare_addr
    input  wire [7:0]       spare_addr,
    output wire [2:0]       spare_count,
    // repair-signature serial port (export/import without re-running BIST)
    input  wire             sig_shift,  // shift the chain once when high (ignored under cfg_clear)
    input  wire             sig_in,
    output wire             sig_out,
    // macro port 0
    output wire             m_csb,
    output wire             m_web,
    output wire [7:0]       m_addr,
    output wire [31:0]      m_din,
    input  wire [31:0]      m_dout
);
    localparam P = 1 << PBITS;

    reg [6*P-1:0]  sel0_flat;
    reg [6*P-1:0]  sel1_flat;
    reg [R-1:0]    sw_valid;
    reg [8*R-1:0]  sw_addr;
    reg [30*R-1:0] sw_data;

    // Repair signature S = {sw_addr, sw_valid, sel1_flat, sel0_flat}, length L = 12*P + 9*R:
    // S[6p +: 6] = sel0 of partition p, S[6*P + 6p +: 6] = sel1 of p, S[12*P + i] = sw_valid[i],
    // S[12*P + R + 8i +: 8] = spare-word address i.  A shift pushes sig_in into S[0] and drops
    // S[L-1] on sig_out, so L shifts with sig_in = sig_out restore the state (export), and L
    // shifts feeding the saved bits MSB first reload it (import).  Spare-word data is not part
    // of the signature: memory contents are lost at reset anyway.
    localparam L = 12*P + 9*R;
    wire [L-1:0] sig_val  = {sw_addr, sw_valid, sel1_flat, sel0_flat};
    wire [L-1:0] sig_next = {sig_val[L-2:0], sig_in};
    assign sig_out = sig_val[L-1];

    // spare_count = popcount(sw_valid); spare words are allocated in index order, so the valid
    // bits form a thermometer code and the count is also the index of the next free word.
    integer p;
    reg [2:0] pcnt;
    always @* begin
        pcnt = 3'd0;
        for (p = 0; p < R; p = p + 1)
            pcnt = pcnt + {2'b00, sw_valid[p]};
    end
    assign spare_count = pcnt;

    // ---------------------------------------------------------------- write path
    wire [PBITS-1:0] w_part = addr[7 -: PBITS];
    wire [5:0]       w_s0   = sel0_flat[6*w_part +: 6];
    wire [5:0]       w_s1   = sel1_flat[6*w_part +: 6];
    wire [29:0]      w_code;
    ecc30_24_enc u_enc (.d(wdata[23:0]), .c(w_code));
    wire [31:0] w_pad = {2'b00, w_code};
    wire [31:0] w_rep = {w_s1[5] & w_pad[w_s1[4:0]], w_s0[5] & w_pad[w_s0[4:0]], w_code};

    assign m_csb  = ~en;
    assign m_web  = ~we;
    assign m_addr = addr;
    assign m_din  = raw ? wdata : w_rep;

    // ---------------------------------------------------------------- read path
    reg       q_rd;
    reg [7:0] q_addr;
    wire [PBITS-1:0] r_part = q_addr[7 -: PBITS];
    wire [5:0]       r_s0   = sel0_flat[6*r_part +: 6];
    wire [5:0]       r_s1   = sel1_flat[6*r_part +: 6];

    reg [29:0] r_code;
    reg        r_hit;
    integer    i;
    always @* begin
        r_code = m_dout[29:0];
        if (r_s0[5]) r_code[r_s0[4:0]] = m_dout[30];
        if (r_s1[5]) r_code[r_s1[4:0]] = m_dout[31];
        r_hit = 1'b0;
        for (i = 0; i < R; i = i + 1)
            if (sw_valid[i] && sw_addr[8*i +: 8] == q_addr) begin
                r_hit  = 1'b1;
                r_code = sw_data[30*i +: 30];
            end
    end

    wire [23:0] r_data;
    wire        r_ce, r_ue;
    ecc30_24_dec u_dec (.c(r_code), .d(r_data), .ce(r_ce), .ue(r_ue));

    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            q_rd <= 1'b0; q_addr <= 8'd0;
            rvalid <= 1'b0; rdata <= 24'd0; rd_ce <= 1'b0; rd_ue <= 1'b0; rraw <= 32'd0;
            sel0_flat <= {6*P{1'b0}}; sel1_flat <= {6*P{1'b0}};
            sw_valid <= {R{1'b0}}; sw_addr <= {8*R{1'b0}}; sw_data <= {30*R{1'b0}};
        end else begin
            q_rd   <= en & ~we;
            q_addr <= addr;
            rvalid <= q_rd;
            if (q_rd) begin
                rdata <= r_data; rd_ce <= r_ce; rd_ue <= r_ue; rraw <= m_dout;
            end
            if (en && we && !raw)
                for (k = 0; k < R; k = k + 1)
                    if (sw_valid[k] && sw_addr[8*k +: 8] == addr) sw_data[30*k +: 30] <= w_code;
            if (cfg_clear) begin
                sel0_flat <= {6*P{1'b0}}; sel1_flat <= {6*P{1'b0}}; sw_valid <= {R{1'b0}};
            end else if (sig_shift) begin
                sel0_flat <= sig_next[6*P-1 : 0];
                sel1_flat <= sig_next[12*P-1 : 6*P];
                sw_valid  <= sig_next[12*P+R-1 : 12*P];
                sw_addr   <= sig_next[L-1 : 12*P+R];
            end else begin
                if (steer_we) begin
                    sel0_flat[6*steer_part +: 6] <= steer_sel0;
                    sel1_flat[6*steer_part +: 6] <= steer_sel1;
                end
                if (spare_we && spare_count < R) begin
                    for (k = 0; k < R; k = k + 1)
                        if (spare_count == k[2:0]) begin
                            sw_valid[k]        <= 1'b1;
                            sw_addr[8*k +: 8]  <= spare_addr;
                        end
                end
            end
        end
    end

    wire unused = r_hit;
endmodule
