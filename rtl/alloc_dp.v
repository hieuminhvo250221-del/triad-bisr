`timescale 1ns/1ps
// Dynamic programme that distributes the R shared spare words over the address windows.
//   best[r]      = minimum total number of ECC-consumed words using at most r spare words so far
//   choice[p][r] = number of spare words given to window p in that optimum (smallest on ties)
// e_flat holds e[q] of the window being added: ECC-consumed words if it receives q spare words
// (63 = impossible).  Sums saturate at 63, which is above any legal budget.
module alloc_dp #(
    parameter PBITS = 4,
    parameter R     = 2
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 init,
    input  wire                 upd,
    input  wire [PBITS-1:0]     part,
    input  wire [6*(R+1)-1:0]   e_flat,
    output wire [5:0]           best_total,
    input  wire [PBITS-1:0]     rd_part,
    input  wire [2:0]           rd_r,
    output wire [2:0]           rd_q
);
    localparam P  = 1 << PBITS;
    localparam CW = 3 * (R + 1);

    reg [6*(R+1)-1:0] best;
    reg [CW*P-1:0]    choice;

    reg [6*(R+1)-1:0] nbest;
    reg [CW-1:0]      npick;
    reg [6:0]         cand;
    reg [5:0]         val;
    reg [2:0]         arg;
    integer           r, q;
    always @* begin
        nbest = {6*(R+1){1'b0}};
        npick = {CW{1'b0}};
        cand  = 7'd0;
        for (r = 0; r <= R; r = r + 1) begin
            val = 6'd63;
            arg = 3'd0;
            for (q = 0; q <= r; q = q + 1) begin
                cand = {1'b0, best[6*(r-q) +: 6]} + {1'b0, e_flat[6*q +: 6]};
                if (cand > 7'd63) cand = 7'd63;
                if (cand[5:0] < val) begin
                    val = cand[5:0];
                    arg = q[2:0];
                end
            end
            nbest[6*r +: 6] = val;
            npick[3*r +: 3] = arg;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            best   <= {6*(R+1){1'b0}};
            choice <= {CW*P{1'b0}};
        end else if (init) begin
            best <= {6*(R+1){1'b0}};
        end else if (upd) begin
            best <= nbest;
            choice[CW*part +: CW] <= npick;
        end
    end

    assign best_total = best[6*R +: 6];
    wire [CW-1:0] row = choice[CW*rd_part +: CW];
    assign rd_q = row[3*rd_r +: 3];
endmodule
