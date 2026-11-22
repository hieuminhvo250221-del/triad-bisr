// Formal checks for the generated Hsiao (30,24) SEC-DED codec (run via formal/ecc.sby).
module ecc_formal;
    (* anyconst *) wire [23:0] d;    // arbitrary data word
    (* anyconst *) wire [4:0]  f0;   // first fault position
    (* anyconst *) wire [4:0]  f1;   // second fault position (double-error case)

    wire [29:0] enc;
    ecc30_24_enc u_enc (.d(d), .c(enc));

    wire [23:0] d0; wire ce0, ue0;
    ecc30_24_dec u_dec0 (.c(enc), .d(d0), .ce(ce0), .ue(ue0));

    wire [29:0] c1 = enc ^ (30'd1 << f0);
    wire [23:0] d1; wire ce1, ue1;
    ecc30_24_dec u_dec1 (.c(c1), .d(d1), .ce(ce1), .ue(ue1));

    wire [29:0] c2 = c1 ^ (30'd1 << f1);
    wire [23:0] d2; wire ce2, ue2;
    ecc30_24_dec u_dec2 (.c(c2), .d(d2), .ce(ce2), .ue(ue2));

    always @* begin
        assume(f0 < 30);
        assume(f1 < 30);
        assume(f0 != f1);
        // no error: data round-trips, nothing corrected or flagged
        assert(d0 == d && !ce0 && !ue0);
        // any single flip of the 30-bit codeword: corrected, correct data, not uncorrectable
        assert(d1 == d && ce1 && !ue1);
        // any two distinct flips: flagged uncorrectable
        assert(ue2);
    end
endmodule
