# Theory of budgeted tri-resource repair

Working notes for the paper (English, plain-text maths). Every statement marked [checked] is exercised
by `model/tests/test_theory.py`, `test_solver.py` or `test_partitioned.py` against exhaustive search.
The proofs are complete arguments but have not been reviewed by anyone else yet.

## 1. Problem

A fault map is a bipartite graph G = (A, B, F): A = words, B = bit columns, (w, c) in F iff bit c of
word w is faulty. deg(w) = number of faulty bits of w; deg(c) = number of faulty words in column c.

TRI-RESOURCE REPAIR (TRR). Given G and integers R, S, K >= 0, are there X subset of A, |X| <= R (words
replaced by spare words) and Y subset of B, |Y| <= S (columns replaced by spare columns) such that
(i) every word w not in X has at most one faulty bit outside Y, and
(ii) the number E(X, Y) of words not in X with exactly one faulty bit outside Y is at most K?

(i) is what a SEC-DED code can absorb; (ii) is the ECC budget: a word counted in E has no correction
capability left for a soft error. K = infinity means "ECC may be used freely". With K = 0 the problem
is the classical spare allocation problem, i.e. Constrained Bipartite Vertex Cover (CBVC) [Kuo and
Fuchs 1986/87; Fernau and Niedermeier 2001; Chen and Kanj 2003]. Optimisation versions: minimise
(E, |X|+|Y|) lexicographically ("reliability first") or (|X|+|Y|, E) ("spare saving").

## 2. Hardness

THEOREM 1. TRR is NP-complete (a) for every fixed K >= 0, (b) for K = infinity, and (c) for K = infinity
even when R = 0.  [checked: the three reductions agree with exhaustive search on random instances]

Proof. Membership in NP is clear. (a) K = 0 is CBVC. For K >= 1 reduce from CBVC: given (G, R, S) add
K gadgets, each a new word with a single fault in a new private column, and keep R, S, K.
If (X, Y) covers G, the K gadget words are the only words with a remaining fault, so E = K.
Conversely let (X, Y) repair the padded instance and let t be the number of gadgets hit by X or Y.
Each such spare covers nothing but its gadget. At least K - t gadgets are counted in E, so at most t
words of G are counted in E; each of them has exactly one remaining fault. Move the t spares, one by
one, from gadgets to these words (a spare word onto the word, a spare column onto the column of its
remaining fault). Budgets are unchanged, the gadgets now account for E = K, and G is covered.
(b) Give every word w a pendant fault in a new private column p_w. A cover (X, Y) of G leaves exactly
the pendant on every word outside X, which ECC absorbs. Conversely, if a repair contains a pendant
column p_w with w not in X, then w has at most one other remaining fault; replace p_w in Y by the
column of that fault (or drop p_w if there is none). After doing this for all pendants, every word
outside X keeps its pendant, hence none of its original faults: (X, Y) covers G.
(c) Let H be any graph. Take one column per vertex and one word per edge {a, b} with faults in
columns a and b. With R = 0 and K = infinity, Y repairs the memory iff Y hits every edge, i.e. iff Y is
a vertex cover of H; VERTEX COVER is NP-complete. QED

Consequence: ECC does not make spare allocation easy, not even without spare words.

## 3. Must-repair rules and the kernel

Let R' and S' denote the spare words/columns still unassigned, and eps = 1 if K >= 1, else 0.

LEMMA 2 (must-repair). In every repair (X, Y):
(M1) a column c with deg(c) > R' + K (counting only words not already forced into X) is in Y;
(M2) a word w with deg(w) > S' + eps (counting only bits not already forced into Y) is in X.

Proof. (M1) If c is not in Y, each of its faulty words is in X or keeps the fault in c and is counted
in E; that is at most R' + K words. (M2) If w is not in X, all but at most one of its faulty bits are
in Y (none may remain if K = 0); that is at most S' + eps bits. QED

Reduction rule (D): after a column is forced into Y, delete its faults; a word left without faults is
removed. Applying M1, M2, D to a fixed point gives the kernel (this is what the hardware fault store
holds; rule D is the "reclaim" of store entries).

THEOREM 3 (kernel size). If the instance is repairable, its kernel has at most
    T(R', S', K) = R' + S' (R' + K) + K
faulty words, hence at most T(R, S, K). For S >= 1 or K >= 1 the bound is attained.
[checked: bound never violated on repairable random maps; explicit tight instances for 45 (R, S, K)]

Proof. Take a repair (X, Y) of the kernel. A faulty kernel word is in X (at most R' words), or has a
fault in a column of Y (each such column is not must-repair, so has at most R' + K faulty words: at
most S' (R' + K) words), or has all faults outside Y; then it has exactly one fault and is counted in E
(at most K words). Tight instance: S columns with R + K single-fault words each; K further words with
one fault each in private columns; R words with two faults each in private columns (one fault each
if S = 0, or if S = 1 and K = 0). No rule fires; replace the R heavy words and the S columns. QED

Remarks. (1) With K = 0 this is the word-count form of the classical 2 kA kB kernel of CBVC, which is
essentially optimal [Jansen, STACS 2016]. (2) Dropping the S K term is wrong (machine-checked).
(3) A fault store with T(R, S, K) entries never overflows on a repairable memory, so overflow is a
proof of unrepairability; this is the early-termination condition.

## 4. Exact algorithms

Call a word outside X with at least two faulty bits outside Y a conflict word.

LEMMA 4 (branching). If w is a conflict word with remaining faults b1, b2, every repair extending
(X, Y) contains w, or column b1, or column b2.
Proof. Otherwise w keeps both faults, violating (i). QED

LEMMA 5 (buy-back). If there is no conflict word, let U be the set of remaining faulty words (one
fault each) and n_c the number of them whose fault is in column c. Spending the remaining spares in
order of decreasing gain (a column gains n_c, a spare word gains 1) is optimal both for "minimise E"
and for "reach E <= K with the fewest spares".
Proof. The words covered by different columns are disjoint, and a spare word covers one word of U, so
the gain of a set of spares is the sum of its individual gains, capped at |U|. For additive gains
the best set of any given size consists of the largest gains. QED

THEOREM 6. Branching by Lemma 4 from the kernel and applying Lemma 5 at every conflict-free node
returns an optimal repair for either objective, after at most 3^(R+S) leaves.
[checked: equal to exhaustive search on 9 000 random maps for both objectives; five seeded bugs caught]

Proof. Every branch spends one spare, so the depth is at most R + S. Let (X*, Y*) be optimal. By
Lemma 4 one can follow, at every conflict, a branch whose choice lies in X* or Y*; the leaf (X0, Y0)
reached is contained in (X*, Y*). The spares of (X*, Y*) outside (X0, Y0) are one feasible buy-back at
that leaf, and Lemma 5 does at least as well. QED

THEOREM 7 (fixed number of columns). TRR and both optimisation versions are solvable in
O(W^S |F|) time: for every Y with |Y| <= S, all conflict words must be in X (reject if more than R),
and the remaining R - |conflict words| spare words are spent on single-fault words, one each.
[checked: equal to the branching solver on 5 000 random maps]

Consequences. (1) Real memories have S <= 2..4, so exact allocation is polynomial in practice: for
W = 30, S = 2 there are 466 column sets. (2) By Theorem 1(c) the exponent S cannot be removed in
general, even for R = 0. (3) Hardware may choose between the search (few nodes, needs a stack) and the
enumeration (no stack, fixed W^S passes over the fault store).

## 5. Address-partitioned steering

The words are split into P partitions by the upper address bits; a spare column may replace a
different bit position in each partition. A repair is X (|X| <= R) and one column set Y_p (|Y_p| <= S)
per partition; (i) and (ii) are evaluated with the Y_p of the word's partition.

PROPOSITION 8. Let e_p(r, s) be the minimum of E for partition p alone with r spare words and s
columns (Theorem 6 with K = infinity). The partitioned instance is repairable iff there are r_p with
sum r_p <= R and sum_p e_p(r_p, S) <= K. The optimum is found by a dynamic programme over the
partitions with state (spare words used, E).
[checked: equal to exhaustive search for P = 2, 4; P = 1 equals the plain solver; finer P never worse]

Proof. Faults of different partitions share neither words nor column choices, so E is additive and
only R and K couple the partitions. QED

The mechanism itself (a spare column steered differently per row partition) is due to Rab, Bawa and
Touba, DFTS 2009; what is added here is the joint exact allocation with spare words and the ECC budget.

## 6. Greedy is not exact

Smallest instance (found by exhaustive search) where repair-most-then-buy-back fails although a
repair exists: R = 0, S = 1, K = 2, words with faulty bits {0}, {2}, {1, 2}. Greedy breaks the tie on
the conflict word in favour of column 1 and is left with three ECC words; replacing column 2 leaves
two. In Monte Carlo the yield loss of greedy is at most 0.40 percentage points (docs/02_g2_report.md).

## 7. Open points

- Review of the proofs of Theorem 1 (a), (b) by a second person.
- Is the branching base 3 improvable (e.g. words with >= 3 remaining faults give vector (1, 2, 2, 2))?
- Spare rows that cover a group of words (physical row with column mux): Lemma 5 no longer applies.
- Compare the search structure with the "hybrid search tree" of Lv et al., IEEE TC 2021 (full text needed).
