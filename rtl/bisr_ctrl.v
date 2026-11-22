`timescale 1ns/1ps
// Self-test / self-repair sequencer (docs/05_architecture.md, section 2).
//   pass 1  analyse : per window: raw March -> bitmap -> option enumeration -> dynamic programme
//   pass 2  allocate: per window (last to first): raw March again, pick the best option for the
//                     number of spare words the dynamic programme granted, program the datapath
//   pass 3  verify  : March on the whole memory through steering, spare words and ECC
module bisr_ctrl #(
    parameter PBITS = 4,
    parameter R     = 2
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start,
    input  wire [4:0]           cfg_k,
    output reg                  busy,
    output reg                  done,
    output reg                  pass,
    output reg  [1:0]           fail_code,   // 0 ok, 1 not repairable within the budget, 2 verification failed
    // March engine
    output wire                 m_start,
    output wire [7:0]           m_base,
    output wire [8:0]           m_len,
    output wire                 m_raw,
    input  wire                 m_done,
    input  wire                 m_fail,
    input  wire                 f_valid,
    // window analyser
    output wire                 en_clear,
    output wire                 en_start,
    output wire [2:0]           en_qsel,
    input  wire                 en_done,
    input  wire [6*(R+1)-1:0]   e_flat,
    input  wire [5:0]           best0,
    input  wire [5:0]           best1,
    input  wire [6:0]           best_nm,
    output wire [7-PBITS:0]     c_idx,
    input  wire                 c_multi,
    input  wire                 c_single,
    // dynamic programme
    output wire                 dp_init,
    output wire                 dp_upd,
    output wire [PBITS-1:0]     dp_part,
    input  wire [5:0]           best_total,
    output wire [2:0]           dp_rd_r,
    input  wire [2:0]           dp_rd_q,
    // datapath configuration
    output wire                 cfg_clear,
    output wire                 steer_we,
    output wire [5:0]           steer_sel0,
    output wire [5:0]           steer_sel1,
    output wire                 spare_we,
    output wire [7:0]           spare_addr
);
    localparam WBITS = 8 - PBITS;
    localparam [3:0] IDLE = 4'd0, P1_GO = 4'd1, P1_MARCH = 4'd2, P1_ENS = 4'd3, P1_ENUM = 4'd4, P1_UPD = 4'd5,
                     DECIDE = 4'd6, P2_GO = 4'd7, P2_MARCH = 4'd8, P2_ENS = 4'd9, P2_ENUM = 4'd10,
                     P2_STEER = 4'd11, P2_SCAN_M = 4'd12, P2_SCAN_S = 4'd13, P3_GO = 4'd14, P3_MARCH = 4'd15;

    reg [3:0]        state;
    reg [PBITS-1:0]  part;
    reg [WBITS-1:0]  idx;
    reg [2:0]        r_rem, q;
    reg [6:0]        need;
    reg              any_fault;

    wire last_part = &part;
    wire last_idx  = &idx;
    wire [5:0] e_q = e_flat[6*q +: 6];

    assign m_start  = (state == P1_GO) | (state == P2_GO) | (state == P3_GO);
    assign m_raw    = (state != P3_GO) & (state != P3_MARCH);
    assign m_base   = m_raw ? {part, {WBITS{1'b0}}} : 8'd0;
    assign m_len    = m_raw ? (9'd1 << WBITS) : 9'd256;
    assign en_clear = (state == P1_GO) | (state == P2_GO);
    assign en_start = (state == P1_ENS) | (state == P2_ENS);
    assign en_qsel  = q;
    assign c_idx    = idx;
    assign dp_init  = (state == IDLE) & start;
    assign dp_upd   = (state == P1_UPD);
    assign dp_part  = part;
    assign dp_rd_r  = r_rem;
    assign cfg_clear  = (state == IDLE) & start;
    assign steer_we   = (state == P2_STEER) & (e_q != 6'd63);
    assign steer_sel0 = best0;
    assign steer_sel1 = best1;
    assign spare_we   = ((state == P2_SCAN_M) & c_multi) | ((state == P2_SCAN_S) & c_single & (need != 7'd0));
    assign spare_addr = {part, idx};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; part <= {PBITS{1'b0}}; idx <= {WBITS{1'b0}};
            r_rem <= 3'd0; q <= 3'd0; need <= 7'd0; any_fault <= 1'b0;
            busy <= 1'b0; done <= 1'b0; pass <= 1'b0; fail_code <= 2'd0;
        end else begin
            done <= 1'b0;
            if (f_valid) any_fault <= 1'b1;
            case (state)
                IDLE: if (start) begin
                    busy <= 1'b1; pass <= 1'b0; fail_code <= 2'd0; any_fault <= 1'b0;
                    part <= {PBITS{1'b0}}; q <= 3'd0; state <= P1_GO;
                end
                P1_GO:    state <= P1_MARCH;
                P1_MARCH: if (m_done) state <= P1_ENS;
                P1_ENS:   state <= P1_ENUM;
                P1_ENUM:  if (en_done) state <= P1_UPD;
                P1_UPD: begin
                    part <= part + 1'b1;
                    state <= last_part ? DECIDE : P1_GO;
                end
                DECIDE: begin
                    if (!any_fault) state <= P3_GO;
                    else if (best_total > {1'b0, cfg_k}) begin
                        busy <= 1'b0; done <= 1'b1; fail_code <= 2'd1; state <= IDLE;
                    end else begin
                        part <= {PBITS{1'b1}}; r_rem <= R[2:0]; state <= P2_GO;
                    end
                end
                P2_GO: begin
                    q <= dp_rd_q; state <= P2_MARCH;
                end
                P2_MARCH: if (m_done) state <= P2_ENS;
                P2_ENS:   state <= P2_ENUM;
                P2_ENUM:  if (en_done) state <= P2_STEER;
                P2_STEER: begin
                    if (e_q == 6'd63) begin   // the fault map changed between the passes
                        busy <= 1'b0; done <= 1'b1; fail_code <= 2'd1; state <= IDLE;
                    end else begin
                        r_rem <= r_rem - q;
                        need  <= {4'd0, q} - best_nm;
                        idx   <= {WBITS{1'b0}};
                        state <= P2_SCAN_M;
                    end
                end
                P2_SCAN_M: begin
                    idx <= idx + 1'b1;
                    if (last_idx) state <= P2_SCAN_S;
                end
                P2_SCAN_S: begin
                    idx <= idx + 1'b1;
                    if (c_single && need != 7'd0) need <= need - 7'd1;
                    if (last_idx) begin
                        part  <= part - 1'b1;
                        state <= (part == {PBITS{1'b0}}) ? P3_GO : P2_GO;
                    end
                end
                P3_GO:    state <= P3_MARCH;
                default: if (m_done) begin   // P3_MARCH
                    busy <= 1'b0; done <= 1'b1; state <= IDLE;
                    pass <= ~m_fail;
                    fail_code <= m_fail ? 2'd2 : 2'd0;
                end
            endcase
        end
    end
endmodule
