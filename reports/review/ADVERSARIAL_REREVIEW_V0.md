# ADVERSARIAL RE-REVIEW V0

Reviewed current main at start: `147372e7f541364f8ed748f8e29281b2d5bff363`

Tested repair HEAD: `3730c6bbd1da10bc82648691ba619ff1b1d12b38`

Pre-fix HEAD: `4b4d4d8048ef3cf95689c4718375e15489419ab8`

Role: `CHAT3_REVIEWER`

Scope: independent re-review of Chat2's A01-A08 repairs, preservation of A09-A12, repair-induced regressions, frozen constants, CI evidence, and message-bus CAS semantics. Terminal-Bench was not run. No implementation, architecture, benchmark, provider configuration, or frozen scientific state was modified by this review.

## 1. VERDICT

`FAIL`

Recommendation: `FIX_THEN_REREVIEW`.

Chat2's CI evidence is genuine and the tested implementation is still byte-identical in the experimental paths on current main. However, the repair is not general enough to clear staging for authoritative mini-SWE-agent integration. Independent variants found surviving failures in A01, A02, A04, A05, and A06, plus a fix-induced candidate-pool monopoly regression. A05 remains a blocker because the required A->B->A pathname race can return `OK` and therefore permit `FRESH`.

This is not a core contradiction. The failures appear locally repairable without changing frozen v0 constants or the high-level architecture.

### Execution qualification

GitHub Actions run `33947583427` is exact repository evidence at repair HEAD `3730c6bb...`. The reviewer execution shell could not clone GitHub because outbound DNS/transport is unavailable. New executable variants were therefore run against a functional transcription of the exact fetched staging modules, with causal paths checked line-by-line against GitHub source. This report does not misrepresent those reviewer runs as a byte-for-byte local checkout.

Independent new variants counted for this re-review: `30 total: 23 PASS, 7 FAIL`. One initially over-strong OBSERVED-vs-VERIFIED assertion was discarded during self-check and is not counted as a failure.

## 2. REPAIR CLAIM AUDIT

| claim | classification | evidence | remaining risk |
|---|---|---|---|
| current main implementation equals tested repair HEAD | VERIFIED | compare `3730c6...` -> `147372e...` changes only Chat2 LAST_SEEN and two handoff messages | none for implementation equivalence |
| CI run 33947583427 succeeded at 3730c6 | VERIFIED | run metadata + job logs | success proves executed fixtures, not generality |
| 85/85 pytest claim | VERIFIED | 37 + 14 + 18 + 16 exact logged test counts | committed tests miss counterexamples below |
| A01 fixed | FALSE | 4,200 duplicate lexical rows starve a distinct relevant target behind `FTS_SCAN_MAX=4096` | finite pre-dedup scan still admits duplicate starvation |
| A02 fixed | FALSE | exact deep signatures work, but stored command whitespace defeats old failed-command recall; error signature substring admits similar non-identical signature | normalization/precision incomplete |
| A03 fixed | VERIFIED for stated invariant | newer relevant VERIFIED numeric correction survives equivalence and can suppress older UNVERIFIED conflict | frozen score/budget may still prefer OBSERVED evidence; that is not classified as an A03 repair defect |
| A04 fixed | FALSE | same scientific text/metadata with different referenced file state still deduplicates | file_paths/file_fingerprints omitted from equivalence |
| A05 fixed | FALSE | A->B->A symlink ABA during one hash returned `OK` in 30/30 probes in reviewer runtime | `_same_identity` checks only dev+ino; detectable lstat metadata changes are ignored |
| A06 fixed | FALSE as general recall claim | recent Straße/STRASSE and Greek sigma variants work; old casefold-only evidence beyond newest-200 supplement is unreachable | normalization-only recall is recency-bounded |
| A07 fixed | VERIFIED for staging additive contract | strict nonnegative exact ints + explicit total equality; missing/inconsistent totals invalid | GLM/TokenRouter semantics still unverified end-to-end |
| A08 fixed | VERIFIED | nested/top-level cache and reasoning branches preserved; raw_usage intact; totals unchanged | eventual provider shape mapping remains integration work |
| A09-A12 preserved | VERIFIED | independent boundary/context/accounting variants pass | integration behavior still separate gate |
| message bus CAS safe | SUPPORTED_BUT_NOT_VERIFIED / PARTIAL | protocol specifies expected-parent commit + non-force ref update; helper only compares caller-supplied SHA strings and CAS tests simulate values | actual safety depends on publisher using non-force ref update and retry protocol |
| staging correct enough for authoritative integration | FALSE | A05 blocker + retrieval/dedup failures + fix-induced monopoly | fix/re-review required |
| token accounting ready for integration testing | SUPPORTED_BUT_NOT_VERIFIED | staging helper now fails closed under frozen additive contract | provider-attempt interception/aggregation not integrated |
| baseline safe | UNVERIFIED | T10 not run | authoritative disabled-path equivalence required |
| benchmark ready | FALSE | integration/T10/upstream/provider accounting/final manifest gates open | Terminal-Bench remains forbidden |

## 3. A01-A12 INDEPENDENT RECHECK

| ID | result | evidence |
|---|---|---|
| A01 | FAIL | small/100 floods pass, but 4,200 exact duplicates ranked before a useful record exhaust the 4,096 FTS scan before diversity can see the target |
| A02 | FAIL | exact old error and exact failed command survive 3,000 newer rows; trailing stored command whitespace breaks indexed recall; similar error signature is admitted by substring |
| A03 | PASS | timeout/retries/ports numeric corrections remain distinct; newer VERIFIED conflict is not destroyed by near-dedup; multiple hypotheses/corrections tested |
| A04 | FAIL | metadata-aware repair preserves outcome/verification/command differences, but different file state/path metadata can still collapse; benign identical duplicates still collapse correctly |
| A05 | FAIL | ordinary retarget/replacement races fail closed, but A->B->A symlink ABA can return OK/FRESH-capable because inode reuse defeats dev+ino-only revalidation |
| A06 | FAIL | recent casefold supplement works; old normalization-only record outside newest-200 supplement is lost while FTS unicode61 cannot recover ß->ss |
| A07 | PASS | valid 10/4/14 accepted; 999, missing, negative, float, bool, string, partial/missing usage rejected; no estimator fallback or silent total repair |
| A08 | PASS | zero/nonzero nested audit details and unknown extra raw fields preserved without altering total |
| A09 | PASS | exactly 64 MiB accepted; +1 byte rejected |
| A10 | PASS | independent canonical synthetic-message sizes 2047/2048/2049 including escaping/non-ASCII match direct UTF-8 byte calculation |
| A11 | PASS | multiple tool outputs including tool error preserved for complete step; incomplete trailing assistant step excluded |
| A12 | PASS | possibly generated response without provider usage yields TOKEN_ACCOUNTING_INVALID and no estimated token counts |

## 4. NEW ADVERSARIAL TESTS

These are variants beyond the committed Chat3 and Chat2 repair suites.

| ID | attack | result | why it matters |
|---|---|---|---|
| R01 | 4,200 exact duplicate lexical rows + distinct target | FAIL | proves A01 still has a hard scan-starvation boundary before diversity |
| R02 | 100 near-duplicates differing punctuation + target | PASS | repair handles ordinary punctuation noise |
| R03 | old exact error signature behind 3,000 newer rows | PASS | indexed explicit error recall works at requested depth |
| R04 | old exact failed command behind 3,000 newer rows | PASS | command index works for exact stored string |
| R05 | old failed command with trailing stored whitespace behind >200 rows | FAIL | query is stripped but SQL compares raw stored command exactly |
| R06 | foreign task with same exact error signature | PASS | task isolation preserved |
| R06B | same task `E_SIG_EXTRA` queried with `E_SIG` | FAIL | substring signature matching creates false explicit relevance |
| R07C | OBSERVED conflict + newer VERIFIED correction | PASS | VERIFIED remains eligible and is not destroyed; selection can still follow frozen score/budget |
| R08 | several UNVERIFIED numeric hypotheses + one newer VERIFIED correction | PASS | relevant verified correction suppresses conflicting older hypotheses |
| R09 | older/newer VERIFIED numeric conflict | PASS | both remain distinct rather than destructive dedup |
| R10 | noncanonical REFUTED-like status visibility probe | PASS | no crash/loss; not treated as a frozen-contract claim |
| R11 | same text/type/status/command but different file states | FAIL | dedup ignores file state, directly failing requested A04 variant |
| R12 | truly benign identical duplicate pair | PASS | repair did not disable dedup globally |
| R13 | symlink A->B->A during same hash | FAIL | fail-closed race guarantee not met; reproduced OK 30/30 in reviewer filesystem probe |
| R14 | same-size regular replacement with restored mtime | PASS | identity revalidation catches ordinary replacement |
| R15 | regular file replaced by symlink to renamed original | PASS | repair catches path-type/identity mutation |
| R16 | inside->outside->inside symlink ABA probe | PASS in observed run | final metadata differed enough to yield UNSTABLE; does not invalidate R13 |
| R17 | old `straße` beyond 200 rows, query `STRASSE` | FAIL | Unicode normalization repair is recent-supplement only |
| R18 | Greek sigma/final-sigma casefold variant | PASS | minimal supplemental normalization handles recent case |
| R19 | accounting type/value edge matrix | PASS | strict additive helper fails closed for malformed values |
| R20 | top-level + nested cache/reasoning zero values | PASS | audit extraction preserves zero-valued detail branches |
| R21 | huge additive integer counts | PASS | arithmetic remains exact; no float coercion |
| R22 | retry attempt 0 missing usage, retry 1 valid usage | PASS per-attempt | individual attempts preserve invalid/valid status; aggregation remains integration gate |
| R23 | exact 64 MiB / +1 byte | PASS | confirms A09 independently |
| R24 | escape-heavy 2047/2048/2049 whole-envelope calculation | PASS | confirms A10 without trusting selection helper alone |
| R25 | multi-tool complete step with tool error + incomplete tail | PASS | confirms A11 structure |
| R26 | generated response missing usage | PASS | confirms A12 fail-closed behavior |
| R27 | 40 explicit signature rows + stronger ordinary lexical target | FAIL | new explicit-first pool construction monopolizes all 40 candidates: fix-induced retrieval starvation |
| R28 | VERIFIED and UNVERIFIED duplicate floods | PASS | diversity handles moderate floods across verification classes |
| R29 | superseded old error + valid replacement | PASS | invalidated historical record is excluded while replacement remains reachable |
| R30 | candidate count under mixed explicit/ordinary flood | PASS for hard cap | candidate pool remains <=40, but composition fairness fails R27 |

Summary: `23 PASS / 7 FAIL`.

## 5. FIX-INDUCED REGRESSIONS

### HIGH — explicit candidate monopoly

The repair now orders all explicit `error_signature` / `failed_command` candidates before all ordinary lexical/task candidates and then truncates to 40. Forty explicit matches can therefore exclude every ordinary candidate, even a stronger exact lexical target. This is new repair complexity and can create retrieval inflation/poisoning.

### HIGH/MEDIUM — failed-command normalization mismatch

The new SQL path uses `command=?` with the query stripped, but stored commands are not normalized on write. Old commands with trailing/leading whitespace can become unreachable once outside the newest-200 supplemental scan, despite later scoring logic comparing stripped commands.

### BOUNDED COST RISK

`FTS_SCAN_MAX=4096` makes acquisition more robust than top-20-before-dedup, but worst-case acquisition now reads/scans thousands of FTS rows and performs repeated equivalence comparisons. This is bounded, not an unbounded full-table scan, and no frozen latency threshold exists. It must still be measured during integration/reproducibility work.

No repair-induced token-accounting regression was found.

## 6. TOKEN ACCOUNTING REVIEW

The staging helper repair is materially improved and passes this re-review under its stated ordinary additive contract:

- requires input, output, total to be exact nonnegative Python integers; booleans/floats/strings are invalid;
- requires `total == input + output`;
- does not synthesize a missing total;
- missing usage for a possibly generated response remains `TOKEN_ACCOUNTING_INVALID`;
- does not subtract cached tokens;
- does not add reasoning tokens onto the provider total;
- preserves raw provider usage unchanged;
- recursively exposes cache/reasoning-containing provider branches for audit.

What is still unverified: GLM/TokenRouter response mapping, every retry/error/partial provider attempt being intercepted exactly once, and aggregation into the experiment primary metric. Therefore staging accounting is suitable for integration testing, not yet benchmark certification.

## 7. FRESHNESS REVIEW

Ordinary A05 variants are improved: A->B, inside->outside, delete/recreate, same-size replacement, and regular->symlink mutations during hashing generally yield `UNSTABLE`/UNKNOWN.

The remaining blocker is ABA pathname mutation. The repair revalidates using final resolved path plus `(st_dev, st_ino)` identity. In the reviewer filesystem, unlink/recreate of the symlink A->B->A reused the symlink inode; final target and open-file inode also matched the initial state, while lstat ctime/mtime changed. Because `_same_identity` ignores those detectable metadata changes, 30/30 probes returned `OK`, making `FRESH` possible despite a mutation during the observed fingerprint operation.

Self-check: the final pathname happens to point back to A, so the end-state bytes match the beginning. Nevertheless, the frozen/documented operation promises fail-closed stability checks, and the re-review explicitly requires A->B->A during one hash not to return FRESH. The implementation has observable evidence of mutation available and does not use it. A05 therefore remains a blocker.

## 8. RETRIEVAL / DEDUP REVIEW

Positive:

- task isolation remains enforced in SQL;
- candidate pool remains capped at 40;
- exact old error and exact failed-command matches can survive 3,000 newer unrelated records;
- numeric contradictions and verification/outcome/command metadata are much less likely to be destructively deduplicated;
- benign duplicates still collapse;
- frozen scoring coefficients are unchanged.

Negative:

1. A01 has moved, not disappeared: a 4,096-row acquisition scan can itself be saturated by equivalent rows before the distinct target is seen.
2. Explicit signature selection can monopolize the final 40-candidate pool and starve ordinary relevant evidence.
3. Error signatures use substring matching after FTS, so `E_SIG` accepts `E_SIG_EXTRA` as an explicit match.
4. Failed-command indexed recall uses raw exact SQL equality inconsistent with the stripped equality used later.
5. Dedup equivalence still omits file_paths/file_fingerprints, so materially different file-state evidence can collapse.
6. Unicode/casefold-only recall remains bounded to the newest 200 supplemental records when FTS unicode61 cannot provide the equivalent token.

These are local algorithmic defects, not evidence for core redesign.

## 9. MESSAGE BUS CAS REVIEW

Classification: `PARTIAL`.

`scripts/message_bus.py` does not itself perform an atomic GitHub publication CAS. `assert_expected_head(expected,current)` merely validates two SHA strings supplied by the caller, and the committed CAS unit tests simulate head movement in local values.

`HANDOFF_PROTOCOL.md` does specify a correct optimistic publication discipline: create a commit whose parent is the observed head and update `main` with a non-force fast-forward ref update; on failure reread/reallocate/retry. If agents actually use that Git ref update path, two sibling commits from the same old head cannot both fast-forward main.

Therefore the coordination design is defensible but not mechanically enforced by `next-id`; direct content writes or callers that bypass the ref-update discipline can still violate the global-ID invariant. This remains a MEDIUM coordination risk, not a scientific core blocker.

## 10. FROZEN-CONSTANT AUDIT

`PASS`.

No change was found to:

- recent_steps = 4;
- retrieval budget = 2048 whole-message local units;
- max chunk = 256;
- max selected records = 8;
- Q_local = 20;
- Q_task = 10;
- candidate_pool_max = 40;
- Jaccard threshold = 0.85;
- ranking weights: lexical 1.00 / file 0.35 / failure 0.30 / evidence 0.15 / importance 0.10;
- SQLite FTS5 `unicode61`;
- zero extra LLM calls;
- task-local memory;
- GLM-5.3;
- Terminal-Bench 3.0;
- primary metric = provider-reported total tokens / successful tasks.

The repair added internal bounds `FTS_SCAN_MAX=4096` and `SIGNATURE_SCAN_MAX=512` plus a command index. These do not silently alter the frozen published constants, although they introduce the behavior/cost risks discussed above.

## 11. REMAINING RISKS

### BLOCKER

- A05: symlink ABA can evade dev+ino-only final identity validation and permit FRESH.

### HIGH

- A01: duplicate acquisition starvation survives above the new 4,096 scan bound.
- A02: normalized failed-command recall is incomplete for old records.
- R27: explicit-signature candidates can monopolize all 40 candidate slots.
- A04: file-state-distinct scientific evidence can still collapse in dedup.

### MEDIUM/LOW

- error-signature substring false positives;
- A06 normalization-only recall is recency bounded;
- message-bus CAS is protocol-enforced rather than helper-enforced;
- 4,096-row diversity acquisition increases worst-case deterministic retrieval work and needs measured integration profiling.

Still open by design:

- T10 native disabled equivalence;
- authoritative mini-SWE-agent integration;
- upstream tests;
- GLM/TokenRouter attempt accounting integration;
- final manifest freeze;
- Terminal-Bench remains NOT RUN.

## 12. FINAL RECOMMENDATION

`FIX_THEN_REREVIEW`

Do not proceed to authoritative mini-SWE-agent integration yet. Chat2 should make only local repairs/regressions for the surviving counterexamples, especially A05 ABA freshness, then return the exact tested repair commit for Chat3 re-review. No core redesign or revert is justified by current evidence.

## SELF-CHECK A — CORRECTNESS

I attempted to invalidate the negative findings:

- The initially failing OBSERVED-vs-VERIFIED tight-budget assertion was removed because it demanded a stronger property than the frozen ranking architecture; VERIFIED only needs to remain eligible/not be destroyed by equivalence. It does.
- A01 at 4,200 rows is not an artificial infinity case: the project's duplicate/memory-explosion attacks explicitly cover thousands of records, and the implementation intentionally chose a 4,096 acquisition bound.
- A05 ABA was repeated 30 times. The final target matches the original, but the operation's own observable lstat metadata changed; under the explicit fail-closed contract that must not be certified stable.
- R27 is not merely a ranking preference: the ordinary candidate is removed before scoring because explicit candidates consume the entire hard pool.

## SELF-CHECK B — ADVERSARIAL

The re-review deliberately varied cardinality, punctuation, verification classes, task IDs, command normalization, signature similarity, file states, ABA races, Unicode age, accounting shapes, and context boundaries. Twenty-three variants passed. The failures are therefore not a blanket rejection of the repairs; they identify specific generalization gaps beyond Chat2's fixtures.

## SELF-CHECK C — EXPERIMENT CONSISTENCY

This review changed no model, architecture constant, benchmark, task selection, provider parameter, primary metric, or implementation file. Terminal-Bench was neither executed nor inspected. The only intended repository writes are this reviewer report, one immutable reviewer-to-orchestrator message, and Chat3's own LAST_SEEN pointer, followed by an append-only board comment.