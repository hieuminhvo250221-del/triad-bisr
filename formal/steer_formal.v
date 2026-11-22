// BMC harness for the steering / spare-word datapath (run via formal/steer.sby).
// triad_datapath at PBITS=1, R=1 over a one-word symbolic memory at anyconst address A.
// The first two cycles write arbitrary-but-known steering entries (anyconst) through the normal
// steer_we port; afterwards the table is constant.  The spare-word table stays free at init
// (spare_we held low) — that is allowed: a read of A is only checked after a write of A, and a
// write of A that finds the spare word in use also fills its data field.
module steer_formal (
    input wire clk
);
    (* anyconst *) wire [7:0]  A;       // the only tracked word
    (* anyconst *) wire [31:0] sa0;     // stuck-at-0 mask of word A
    (* anyconst *) wire [31:0] sa1;     // stuck-at-1 mask of word A
    wire [31:0] sa = sa0 | sa1;

    // steering entries written during configuration, one per partition
    (* anyconst *) wire [5:0] s0_cfg0, s0_cfg1, s1_cfg0, s1_cfg1;

    (* anyseq *) wire        en;
    (* anyseq *) wire        we;
    (* anyseq *) wire [7:0]  addr;
    (* anyseq *) wire [23:0] wdata;

    // configuration phase: two cycles, one steering write each
    reg [1:0] cfg_step;
    initial cfg_step = 2'd0;
    always @(posedge clk)
        if (cfg_step != 2'd3)
            cfg_step <= cfg_step + 2'd1;
    wire cfg_busy = (cfg_step < 2);
    wire steer_we = cfg_busy;
    wire steer_part = cfg_step[0];
    wire [5:0] steer_sel0 = cfg_step[0] ? s0_cfg1 : s0_cfg0;
    wire [5:0] steer_sel1 = cfg_step[0] ? s1_cfg1 : s1_cfg0;

    wire [23:0] rdata;
    wire        rvalid, rd_ce, rd_ue;
    wire [31:0] rraw;
    wire [2:0]  spare_count;
    wire        sig_out;
    wire        m_csb, m_web;
    wire [7:0]  m_addr;
    wire [31:0] m_din;
    wire [31:0] m_dout;

    triad_datapath #(.PBITS(1), .R(1)) u_dpath (
        .clk(clk), .rst_n(1'b1),
        .en(en), .we(we), .raw(1'b0), .addr(addr), .wdata({8'd0, wdata}),
        .rvalid(rvalid), .rdata(rdata), .rd_ce(rd_ce), .rd_ue(rd_ue), .rraw(rraw),
        .cfg_clear(1'b0), .steer_we(steer_we), .steer_part(steer_part),
        .steer_sel0(steer_sel0), .steer_sel1(steer_sel1),
        .spare_we(1'b0), .spare_addr(8'd0),
        .spare_count(spare_count),
        .sig_shift(1'b0), .sig_in(1'b0), .sig_out(sig_out),
        .m_csb(m_csb), .m_web(m_web), .m_addr(m_addr), .m_din(m_din), .m_dout(m_dout)
    );

    // ------------------------------------------------- one-word memory model
    // Writes apply the stuck masks; a read request launches the stored word on the next cycle.
    reg [31:0] mem;
    reg [31:0] dout_r;
    always @(posedge clk) begin
        if (!m_csb && !m_web && m_addr == A)
            mem <= (m_din & ~sa0) | sa1;
        if (!m_csb && m_web)
            dout_r <= (m_addr == A) ? mem : 32'd0;
    end
    assign m_dout = dout_r;

    // ------------------------------------------------- read-after-write tracking
    reg        pending;                 // a read of A is in flight
    reg        wr_done;                 // a write of A has completed
    reg [23:0] expect;                  // data of the last write to A
    initial begin
        pending = 1'b0;
        wr_done = 1'b0;
    end
    always @(posedge clk) begin
        if (en && we) begin
            wr_done <= 1'b1;
            expect  <= wdata;
        end
        if (en && !we)
            pending <= 1'b1;
        else if (rvalid)
            pending <= 1'b0;

        assume((sa0 & sa1) == 32'd0);   // stuck masks are disjoint
        assume(!(cfg_busy && en));      // no user request until the table is written
        assume(!en || addr == A);       // all requests target A
        assume(!pending || !en);        // no intervening request while a read is in flight
        assume(!(en && !we) || wr_done);// reads of A follow a write of A

        if (pending && rvalid) begin
            assert(rdata == expect);
            assert(!rd_ue);
        end
    end

    // ------------------------------------------------- repair-state assumptions
    // Steering entries of A's partition (PBITS=1 -> partition = A[7]); the values are the
    // harness constants that were written into the table during configuration.
    wire [5:0] s0 = A[7] ? s0_cfg1 : s0_cfg0;
    wire [5:0] s1 = A[7] ? s1_cfg1 : s1_cfg0;
    reg  [29:0] eff;
    always @* begin
        eff = sa[29:0];
        if (s0[5]) begin
            assume(s0[4:0] < 30);
            eff[s0[4:0]] = 1'b0;        // the steered column no longer contributes
            assume(!sa[30]);            // a spare column in use is fault-free
        end
        if (s1[5]) begin
            assume(s1[4:0] < 30);
            eff[s1[4:0]] = 1'b0;
            assume(!sa[31]);
        end
        if (s0[5] && s1[5])
            assume(s0[4:0] != s1[4:0]); // distinct columns
        // after removing the steered columns, at most one faulty bit remains
        assume((eff & (eff - 30'd1)) == 30'd0);
    end
endmodule
