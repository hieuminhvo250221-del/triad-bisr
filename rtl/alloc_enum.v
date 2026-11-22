`timescale 1ns/1ps
// Classification of one word under a steering option: o = {valid, column} per spare column.
// The fault vector of the codeword takes the spare column's own fault bit at the steered position.
module word_class (
    input  wire [31:0] row,
    input  wire [5:0]  o0,
    input  wire [5:0]  o1,
    output wire        multi,   // two or more faulty bits left: needs a spare word
    output wire        single   // exactly one faulty bit left: ECC, or a spare word if one is left over
);
    reg [29:0] v;
    always @* begin
        v = row[29:0];
        if (o0[5]) v[o0[4:0]] = row[30];
        if (o1[5]) v[o1[4:0]] = row[31];
    end
    assign multi  = |(v & (v - 30'd1));
    assign single = (|v) & ~multi;
endmodule

// Fault bitmap of one address window and exhaustive evaluation of its steering options.
// One option per clock cycle, 31 x 31 slots: c0 outer, c1 inner, "unused" first, then columns in
// ascending order; only columns that have a fault in the window are considered.  For every number
// q of spare words, e[q] is the minimum number of ECC-consumed words (63 = impossible); the first
// option reaching e[q_sel] is kept in (best0, best1) together with its number of conflict words.
module alloc_enum #(
    parameter WBITS = 4,   // window of 2**WBITS words
    parameter R     = 2
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               clear,
    input  wire               f_valid,
    input  wire [WBITS-1:0]   f_idx,
    input  wire [31:0]        f_diff,
    input  wire               start,
    input  wire [2:0]         q_sel,
    output reg                busy,
    output reg                done,
    output reg  [6*(R+1)-1:0] e_flat,
    output reg  [5:0]         best0,
    output reg  [5:0]         best1,
    output reg  [6:0]         best_nm,
    input  wire [WBITS-1:0]   c_idx,
    output wire               c_multi,
    output wire               c_single
);
    localparam WIN = 1 << WBITS;
    reg [32*WIN-1:0] bm;

    reg [29:0] uni;
    integer    u;
    always @* begin
        uni = 30'd0;
        for (u = 0; u < WIN; u = u + 1) uni = uni | bm[32*u +: 30];
    end

    reg  [4:0] i0, i1;   // 0 = spare column unused, n = replace column n-1
    wire [4:0] c0 = i0 - 5'd1;
    wire [4:0] c1 = i1 - 5'd1;
    wire [5:0] o0 = (i0 == 5'd0) ? 6'd0 : {1'b1, c0};
    wire [5:0] o1 = (i1 == 5'd0) ? 6'd0 : {1'b1, c1};
    wire       ok0 = (i0 == 5'd0) | uni[c0];
    wire       ok1 = (i1 == 5'd0) | uni[c1];
    wire       valid = ok0 & ok1 & ~((i0 != 5'd0) & (i0 == i1));

    wire [WIN-1:0] wm, ws;
    genvar g;
    generate
        for (g = 0; g < WIN; g = g + 1) begin : g_word
            word_class u_wc (.row(bm[32*g +: 32]), .o0(o0), .o1(o1), .multi(wm[g]), .single(ws[g]));
        end
    endgenerate

    function [6:0] count;
        input [WIN-1:0] x;
        integer n;
        begin
            count = 7'd0;
            for (n = 0; n < WIN; n = n + 1) count = count + {6'd0, x[n]};
        end
    endfunction
    wire [6:0] nm = count(wm);
    wire [6:0] ns = count(ws);

    reg [6*(R+1)-1:0] e_next;
    reg [R:0]         better;
    reg [6:0]         room, val;
    integer           q;
    always @* begin
        e_next = e_flat;
        better = {(R+1){1'b0}};
        room   = 7'd0;
        val    = 7'd0;
        for (q = 0; q <= R; q = q + 1) begin
            if (valid && (q[6:0] >= nm)) begin
                room = q[6:0] - nm;
                val  = (ns > room) ? (ns - room) : 7'd0;
                if (val > 7'd63) val = 7'd63;
                if (val[5:0] < e_flat[6*q +: 6]) begin
                    e_next[6*q +: 6] = val[5:0];
                    better[q] = 1'b1;
                end
            end
        end
    end
    wire [7:0] better_pad = {{(7-R){1'b0}}, better};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bm <= {32*WIN{1'b0}};
            busy <= 1'b0; done <= 1'b0;
            e_flat <= {(R+1){6'd63}};
            best0 <= 6'd0; best1 <= 6'd0; best_nm <= 7'd0;
            i0 <= 5'd0; i1 <= 5'd0;
        end else begin
            done <= 1'b0;
            if (clear) bm <= {32*WIN{1'b0}};
            else if (f_valid) bm[32*f_idx +: 32] <= bm[32*f_idx +: 32] | f_diff;
            if (start) begin
                busy <= 1'b1;
                i0 <= 5'd0; i1 <= 5'd0;
                e_flat <= {(R+1){6'd63}};
                best0 <= 6'd0; best1 <= 6'd0; best_nm <= 7'd0;
            end else if (busy) begin
                e_flat <= e_next;
                if (better_pad[q_sel]) begin
                    best0 <= o0; best1 <= o1; best_nm <= nm;
                end
                if (i1 != 5'd30) i1 <= i1 + 5'd1;
                else begin
                    i1 <= 5'd0;
                    if (i0 != 5'd30) i0 <= i0 + 5'd1;
                    else begin
                        busy <= 1'b0; done <= 1'b1;
                    end
                end
            end
        end
    end

    word_class u_cls (.row(bm[32*c_idx +: 32]), .o0(best0), .o1(best1), .multi(c_multi), .single(c_single));
endmodule
