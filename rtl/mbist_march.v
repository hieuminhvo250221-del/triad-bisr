`timescale 1ns/1ps
// March C- over the address range [base, base+len):
//   {any(w0); up(r0,w1); up(r1,w0); down(r0,w1); down(r1,w0); any(r0)}, repeated for `nbg` data
//   backgrounds (1..6) so that coupling between bits of one word is covered as well.
// A write takes one cycle, a read three (read data returns two clock edges after the request).
//   raw = 1: 32 physical bits are written and compared; every failing read is reported as
//            (f_addr, f_diff), f_diff = expected ^ actual.
//   raw = 0: the 24-bit user word goes through steering, spare words and ECC; `fail` is set when a
//            read returns wrong data or an uncorrectable error.
module mbist_march (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [7:0]  base,
    input  wire [8:0]  len,
    input  wire        raw,
    input  wire [2:0]  nbg,
    output reg         busy,
    output reg         done,
    output reg         fail,
    // request to the datapath (combinational)
    output wire        req_en,
    output wire        req_we,
    output wire [7:0]  req_addr,
    output wire [31:0] req_wdata,
    input  wire [23:0] rdata,
    input  wire        rd_ue,
    input  wire [31:0] rraw,
    // fault report, raw mode
    output reg         f_valid,
    output reg  [7:0]  f_addr,
    output reg  [31:0] f_diff
);
    localparam S_IDLE = 2'd0, S_REQ = 2'd1, S_WAIT = 2'd2, S_CHK = 2'd3;
    reg [1:0] state;
    reg [2:0] elem;     // March element 0..5
    reg       second;   // 1: the write that follows the read of this element
    reg [8:0] idx;
    reg [2:0] bg;

    wire e_read  = (elem != 3'd0);
    wire e_write = (elem != 3'd5);
    wire e_down  = (elem == 3'd3) | (elem == 3'd4);
    wire e_rval  = (elem == 3'd2) | (elem == 3'd4);   // value the read expects
    wire e_wval  = (elem == 3'd1) | (elem == 3'd3);   // value the write stores
    wire is_write = e_read ? second : 1'b1;

    reg [31:0] bgpat;
    always @* begin
        case (bg)
            3'd0:    bgpat = 32'h0000_0000;
            3'd1:    bgpat = 32'h5555_5555;
            3'd2:    bgpat = 32'h3333_3333;
            3'd3:    bgpat = 32'h0F0F_0F0F;
            3'd4:    bgpat = 32'h00FF_00FF;
            default: bgpat = 32'h0000_FFFF;
        endcase
    end
    wire [31:0] pat_w = e_wval ? ~bgpat : bgpat;
    wire [31:0] pat_r = e_rval ? ~bgpat : bgpat;
    wire [8:0]  last  = len - 9'd1;
    wire [8:0]  off   = e_down ? (last - idx) : idx;
    wire [7:0]  cur   = base + off[7:0];

    assign req_en    = (state == S_REQ);
    assign req_we    = is_write;
    assign req_addr  = cur;
    assign req_wdata = pat_w;

    wire advance = ((state == S_REQ) & is_write) | (state == S_CHK);
    wire [2:0] bg_next = bg + 3'd1;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE; elem <= 3'd0; second <= 1'b0; idx <= 9'd0; bg <= 3'd0;
            busy <= 1'b0; done <= 1'b0; fail <= 1'b0;
            f_valid <= 1'b0; f_addr <= 8'd0; f_diff <= 32'd0;
        end else begin
            done    <= 1'b0;
            f_valid <= 1'b0;
            case (state)
                S_IDLE: if (start) begin
                    busy <= 1'b1; fail <= 1'b0;
                    elem <= 3'd0; second <= 1'b0; idx <= 9'd0; bg <= 3'd0;
                    state <= S_REQ;
                end
                S_REQ:  if (!is_write) state <= S_WAIT;
                S_WAIT: state <= S_CHK;
                default: begin  // S_CHK: the read data is valid now
                    if (raw) begin
                        if (rraw != pat_r) begin
                            f_valid <= 1'b1; f_addr <= cur; f_diff <= rraw ^ pat_r;
                        end
                    end else if (rdata != pat_r[23:0] || rd_ue) fail <= 1'b1;
                end
            endcase
            if (advance) begin
                state <= S_REQ;
                if (e_read && e_write && !second) second <= 1'b1;
                else begin
                    second <= 1'b0;
                    if (idx != last) idx <= idx + 9'd1;
                    else begin
                        idx <= 9'd0;
                        if (elem != 3'd5) elem <= elem + 3'd1;
                        else if (bg_next != nbg) begin
                            elem <= 3'd0; bg <= bg_next;
                        end else begin
                            busy <= 1'b0; done <= 1'b1; state <= S_IDLE;
                        end
                    end
                end
            end
        end
    end
endmodule
