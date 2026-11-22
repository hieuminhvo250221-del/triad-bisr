`timescale 1ns/1ps
// Simulation model of the OpenRAM macro with injectable stuck-at faults.
// Same ports and edge behaviour as the PDK model: inputs are sampled on the rising edge, the access
// happens on the falling edge, dout is valid from then until shortly after the next rising edge.
// Fault injection: bit b of word a reads 0 if sa0[a][b] = 1 and reads 1 if sa1[a][b] = 1.
module sky130_sram_1kbyte_1rw1r_32x256_8 (
`ifdef USE_POWER_PINS
    inout             vccd1,
    inout             vssd1,
`endif
    input             clk0,
    input             csb0,
    input             web0,
    input      [3:0]  wmask0,
    input      [7:0]  addr0,
    input      [31:0] din0,
    output reg [31:0] dout0,
    input             clk1,
    input             csb1,
    input      [7:0]  addr1,
    output reg [31:0] dout1
);
    reg [31:0] mem [0:255];
    reg [31:0] sa0 [0:255];
    reg [31:0] sa1 [0:255];

    reg        csb0_r, web0_r, csb1_r;
    reg [3:0]  wmask0_r;
    reg [7:0]  addr0_r, addr1_r;
    reg [31:0] din0_r;
    integer    i;

    initial begin
        for (i = 0; i < 256; i = i + 1) begin
            mem[i] = 32'h0;
            sa0[i] = 32'h0;
            sa1[i] = 32'h0;
        end
        csb0_r = 1'b1; web0_r = 1'b1; csb1_r = 1'b1;
    end

    wire [31:0] wbits = {{8{wmask0_r[3]}}, {8{wmask0_r[2]}}, {8{wmask0_r[1]}}, {8{wmask0_r[0]}}};

    always @(posedge clk0) begin
        csb0_r   <= csb0;
        web0_r   <= web0;
        wmask0_r <= wmask0;
        addr0_r  <= addr0;
        din0_r   <= din0;
        dout0    <= #1 32'bx;
    end

    always @(negedge clk0) begin
        if (!csb0_r && !web0_r)
            mem[addr0_r] <= (mem[addr0_r] & ~wbits) | (din0_r & wbits);
        if (!csb0_r && web0_r)
            dout0 <= #3 (mem[addr0_r] & ~sa0[addr0_r]) | sa1[addr0_r];
    end

    always @(posedge clk1) begin
        csb1_r  <= csb1;
        addr1_r <= addr1;
        dout1   <= #1 32'bx;
    end

    always @(negedge clk1)
        if (!csb1_r)
            dout1 <= #3 (mem[addr1_r] & ~sa0[addr1_r]) | sa1[addr1_r];
endmodule
