# The stack ADR: the native implementation stack of AIEOS

> - **Status:** decided: Go. Decided by: decision agent (A41, A51), decision D-978, 2026-10-16, a delegated approval in the owner's place with advisory effect (DM F47), relayed to the owner in plain words; the owner can overturn it in one sentence (A51 item (6)). Advisory, like the other documents in `docs/plan/`. The owner's own parts were the criteria and weights (given on 2026-10-15), criterion 8's score and whether criterion 5 is left unscored (decisions D-903, D-975); the owner's answer of 2026-10-16, "1 có/ 2 không chấm", read in decision D-978 as criterion 5 left unscored and criterion 8 not scored.
> - **Sources:** DM A8, A10, A11 and C12 (`docs/pre-genesis/decision-matrix.md` lines 64, 66, 67 and 185); CR-001 E6 (`docs/pre-genesis/CR-001-concept-errata.md` line 15); Master Plan §4 (the benchmark and the stack ADR); `docs/plan/m4-exit-review.md` §6 and §7 (the criteria, the owner's weights at lines 74-83 and the owner's answer at lines 92-97); `docs/plan/bench-results-round1.md` (R1) and `docs/plan/bench-results-round2.md` (R2); decisions D-794, D-903, D-905, D-975 and D-978.

## 1. Context

- A8: the stack is chosen by a TS / Go / Rust benchmark; the owner approves the criteria and weights before the run (done, 2026-10-15). A10: Python bootstrap → benchmark → native stack selection → native implementation. A11: native takes over per capability, through shadow and assisted stages, proven by conformance. C12: the native implementation stack, decided by this record (DM F47). CR-001 E6: the first language is decided by this ADR, after the benchmark.
- The benchmark ran in two rounds (R1, R2): the governor's acceptance decision and the Resume Check over the 30 frozen fixtures; the event log's append and recovery over a generated log. Each port was written by a fresh AI agent from one brief and reviewed five times from one template.
- What the choice changes now: the language of the native versions that reach the "shadow" stage in v0.1 (Master Plan §4, M8: the governor and the Resume Check first). The bootstrap stays the working implementation of v0.1 (Option C, 2026-10-15).

## 2. Results per criterion

| # | Criterion | The owner's weight | TypeScript | Go | Rust | Sources |
|---|---|---|---|---|---|---|
| 1 | Correctness (byte-equal records) | must | pass, both rounds, Linux and Windows | pass | pass | R1 §2.1; R2 §2.1 |
| 2 | Supply-chain size | cao | 0 run-time packages, 1 build-time tool (the type checker) | 0 and 0 | 0 and 0 | R1 §2.2; R2 §2.2 |
| 3 | Distribution (one file) | thấp | no (a runtime to install), a reading | yes, a reading | yes, a reading | R1 §2.3; R2 §2.3 |
| 4 | Windows and Linux the same | vừa | same on both, both rounds | same | same | R1 §2.4; R2 §2.4 |
| 5 | Speed | thấp | not scored (the owner's answer, 2026-10-16) | not scored | not scored | R1 §2.5; R2 §2.5 |
| 6 | AI writes and reviews it (counted findings, round 1 + round 2) | cao | 18 + 3 = 21 | 19 + 3 = 22 | 19 + 6 = 25 | R1 §2.6; R2 §2.6 |
| 7 | Type and memory safety | thấp | types at build time only, a reading | types and managed memory, a reading | types and memory checked by the compiler, a reading | R1 §2.7; R2 §2.7 |
| 8 | Ease for the owner to read and maintain | vừa | not scored (the owner's answer, 2026-10-16) | not scored | not scored | R1 §2.8; R2 §2.8 |

Criterion 6 is AI-judged (CR-002 K6), not a human measure, and the two rounds are different workloads; each round's counts are shown in R1 and R2.

## 3. The numbers (criteria 1 to 4, 6 and 7; criteria 5 and 8 not scored)

- **Method (the decision agent's reading, not the owner's):** the owner's words are turned into numbers cao 3, vừa 2, thấp 1; each criterion's value is turned into 0 to 1: criterion 2 as 1/(1 + packages and tools), criterion 3 yes 1 / no 0, criterion 4 pass 1, criterion 6 the fewest counted findings divided by the port's own, criterion 7 by the reading Rust 1, Go 2/3, TypeScript 1/3. The script and its output are kept outside the repository with the decision that approved this text.
- **Result:** TypeScript 6.833, Go 9.530, Rust 9.520 (out of 13 for these criteria). Go and Rust are within 0.01 of each other, well inside what any change of method could move (for example, criterion 7's reading or criterion 2's formula), so this record treats them as a tie, settled in §5 by reasons, not by the number; TypeScript is behind on supply chain, distribution and safety, and could not have led under any criterion-8 ranking (its highest total, 8.833, is below Go's and Rust's lowest).

## 4. Options

- **TypeScript:** rejected: the only port with a build-time tool to fetch and check, no single-file program, and types checked at build time only; its fewest review findings (criterion 6) do not make up for them.
- **Go:** chosen (§5).
- **Rust:** rejected: its edge is the strongest compile-time checks, on criterion 7, which the owner weighted low; it has more counted review findings (6 in round 2 against Go's 3; 25 over both rounds against Go's 22), and it reached zero packages by hand-writing its own SHA-256.

## 5. Decision

**The native implementation stack of AIEOS is Go.** Decided by: decision agent (A41, A51), decision D-978, 2026-10-16. The reasons, since the numbers tie:
- **Criterion 6 (cao):** Go has fewer counted review findings than Rust in round 2 (3 against 6) and over both rounds (22 against 25). It is AI-judged (CR-002 K6), so it counts as a direction, not a measure.
- **Criterion 2 (cao), read for its purpose** (INV-002's spirit, `docs/plan/m4-exit-review.md` line 77): both ports use no third-party package, but Rust reached that by writing its own SHA-256, while Go uses its standard library's `crypto/sha256` (DEF-0063; the port brief's revision 3). AIEOS binds evidence by hashes, so hand-written cryptography is code to maintain and trust; Go's standard library keeps both the package count and the hand-written surface small. A reading, not a scored number.
- **Criterion 7 (thấp):** Rust's stronger compile-time checks are its real advantage; the owner weighted that criterion low, and Go's managed memory, with no unsafe package used, covers the main memory-safety risk.
- **Size, for reference only** (criterion 8 not scored): the Go port is smaller (6512 lines against 7609 at commit 049af36f, R2 §2.8).

## 6. Limits

- Every writer and reviewer is an AI of one vendor; the ports were written in order (round 1 TypeScript, Go, Rust; round 2 Rust, Go, TypeScript); the runners' toolchains are not pinned; each port's own limits are in R1 §3, R2 §3 and DEF-0063, among them the Go port's open fidelity question on a year below 1000.
- The numbers of §3 depend on a method the owner did not give; they rank, they do not measure. Criteria 5 and 8 were not scored, by the owner's answer.
- The choice is advisory and starts at the "shadow" stage (Master Plan §4, M8): the bootstrap stays the working implementation, so a later reversal costs the native ports, not the bootstrap.
