# ADVERSARIAL REVIEW V0

Reviewed source commit: `7021eddd0b6f41483de5ce078931f17a32e9fc05`

Role: `CHAT3_REVIEWER`

Scope: staging implementation, staging tests, provenance, token-accounting helper, and message bus. Terminal-Bench was not run. Frozen experimental variables were not changed.

## 1. VERDICT

`FAIL`

The repository is not ready for authoritative mini-SWE-agent integration as currently staged. The existing 37-test suite is useful but has important false-pass gaps. New deterministic adversarial cases expose failures in candidate generation, evidence conflict handling, freshness fail-closed behavior, and token-accounting validation.

This is **not** a `CORE_CONTRADICTION`. Every demonstrated defect appears locally repairable without changing the frozen v0 architecture, model, benchmark, primary metric, or task selection.

Recommended disposition: `FIX_THEN_INTEGRATE`.

### Evidence execution qualification

The GitHub source was inspected directly at the reviewed commit. Native Git transport from the execution shell could not materialize the repository, so the new executable adversarial cases were run against a functional transcription of the fetched staging modules. Static causal paths were then checked against the exact current GitHub source. Therefore the new failures are valid counterexamples to the fetched logic, but this review does **not** claim an independent byte-for-byte rerun of Chat 2's 37-test suite.

New adversarial execution result: `12 cases: 4 PASS, 8 FAIL`.

Additional bounded scale probe: 3,001 records produced an approximately 1.09 MiB SQLite database and one rare-old-record retrieval took approximately 189 ms in the reviewer runtime. This is descriptive only; no frozen latency threshold exists.

## 2. CLAIM AUDIT

| claim | classification | evidence | weakness |
|---|---|---|---|
| current reviewed `main` was `7021eddd...` | VERIFIED | GitHub ref read at start and pre-publication check | none observed |
| `36/36 canonical snapshot files exact` | SUPPORTED_BUT_NOT_VERIFIED | SHA-256 manifest exists; correction commit repaired four known byte mismatches; current blobs are present | reviewer could not independently recompute all 36 SHA-256 values from a byte-for-byte materialized current tree |
| provenance distinguishes local SHAs from remote SHAs | VERIFIED | `provenance/LOCAL_CANONICAL_HISTORY.md` explicitly states local SHAs are provenance identifiers, not remote commit IDs | local Git objects are not in the remote repo, so mapping is documentary rather than object-identical |
| intermediate four bad imports contaminate executable staging semantics | FALSE | correction commit changes to the four known mismatches were comments only | exact-byte evidence before correction is still non-canonical and must not be cited as snapshot-exact evidence |
| `37 staging tests PASS` on the original isolated tree | SUPPORTED_BUT_NOT_VERIFIED | committed staging report records 37 PASS and repo-equivalent command | reviewer did not independently rerun the exact current blobs; passing fixtures also do not prove the broader invariants |
| T1-T9 fixture set proves the intended invariants generally | FALSE | new counterexamples defeat duplicate-flood robustness, old-error recall, evidence priority, freshness, and accounting | original fixtures are narrow happy-path representatives |
| T5a-T5h fixtures cover fail-closed freshness | FALSE | symlink retarget during an open-file hash can return `FRESH` | existing tests change target before hashing or mutate the opened inode, not the pathname-to-inode binding during hashing |
| `14 message-bus tests PASS` for the listed deterministic cases | SUPPORTED_BUT_NOT_VERIFIED | report and source contain 14 matching tests | no concurrent allocator/publisher test; passing listed cases does not prove race freedom |
| secret scan PASS | SUPPORTED_BUT_NOT_VERIFIED | Chat 2 handoff/board evidence reports it | not independently rerun by Chat 3 |
| staging memory components exist and substantially reflect v0 | VERIFIED | `store.py`, `retrieve.py`, `fingerprint.py`, `context_builder.py`, schema and tests present | correctness of several invariants is false under adversarial inputs |
| memory architecture is correctly implemented | FALSE | verified-evidence conflict and fail-closed freshness counterexamples | components are staged, but correctness claim is too strong |
| baseline safe | UNVERIFIED | canonical state explicitly says T10 NOT VERIFIED | no authoritative disabled-path equivalence test exists |
| token accounting ready for primary metric | FALSE | inconsistent provider total is accepted as `OK`; nested cache/reasoning detail extraction is incomplete; no end-to-end retry aggregation | primary metric cannot rely on this helper yet |
| benchmark ready | FALSE | integration incomplete, T10 not run, provider accounting unverified, final manifest not frozen | Terminal-Bench must remain untouched |
| T10 = NOT VERIFIED | VERIFIED | canonical project state and architecture delta | none |
| authoritative mini-SWE-agent integration = NOT COMPLETE | VERIFIED | canonical project state | none |
| Terminal-Bench = NOT RUN | VERIFIED | canonical project state and frozen variables | reviewer did not run it |
| final manifest = NOT FROZEN | VERIFIED | canonical project state / pre-manifest contains null final fields | none |

## 3. TEST AUDIT

| test | actually proves | does not prove | false-pass risk |
|---|---|---|---|
| `test_t1_forgotten_error` | one old exact lexical error is retrieved | old error survives >200 newer records or lexical mismatch | HIGH |
| `test_t2_distractor_flood` | 100 non-overlapping banana distractors do not hide a rare exact target | keyword-overlap poisoning / duplicate candidates | HIGH |
| `test_t3_duplicate_flood` | selected results collapse 20 identical records when nothing else competes | duplicates cannot consume the FTS candidate budget before dedup | HIGH |
| `test_t4_conflicting_evidence_newer_verified_wins` | its specific verbose verified record wins at a constrained budget | numeric-only conflict, FTS length effects, near-dedup conflict | HIGH |
| `test_supersedes_invalidates_old_record` | explicit `supersedes` invalidates one prior record | implicit conflict resolution without explicit supersedes | MEDIUM |
| `test_t5a_normal_mutation` | ordinary changed hash => stale | path race / replacement during read | MEDIUM |
| `test_t5b_same_size_mutation` | same-size changed content => stale | race during pathname resolution/open | MEDIUM |
| `test_t5c_restored_mtime_mutation` | SHA catches content change despite restored mtime | adversarial pathname retarget | MEDIUM |
| `test_t5d_deletion` | missing current file => unknown | deletion/recreate during open hash | MEDIUM |
| `test_t5e_rename` | old path missing after rename => unknown | rename/replacement race during hash | MEDIUM |
| `test_t5f_symlink_target_change` | symlink target changed before fingerprint => stale | symlink retarget while old target fd is open | HIGH |
| `test_t5g_too_large` | 64 MiB + 1 byte rejected | exact 64 MiB accepted | LOW; reviewer A09 covers boundary |
| `test_t5h_unreadable` | no read permission bits => unreadable | permission race after checks/open | MEDIUM |
| `test_current_state_stale_is_excluded_but_historical_error_retained` | one stale state record excluded while stale historical test result remains labeled | every current-state type/status permutation | MEDIUM |
| `test_t6_loop_prevention_failed_command_signature` | failed-command memory receives a match bonus | agent actually avoids repeating the failed command | HIGH |
| `test_t7_exact_serialized_budget` | implementation serializer reports <=2048 for tested records | independence from same serializer helper; arbitrary escape-heavy exact boundaries | MEDIUM; reviewer A10 independently checks 2047/2048/2049 serializer sizes |
| `test_t8_no_relevant_memory_and_no_message` | one lexical-negative case yields no memory user message | provider-facing empty-retrieval identity | MEDIUM |
| `test_t9_message_structure_and_structural_injection` | one injected string remains content in one synthetic user message and simple tool IDs survive | authoritative provider request, multiple tool outputs/actions, unusual native roles | HIGH |
| `test_last4_no_memory_roles` | helper emits last four complete simple steps with no memory object | true native baseline bypass; no DB/fingerprint/context side effects | HIGH |
| `test_empty_db` | empty DB returns none | absent DB / initialization side effects | LOW |
| `test_single_record` | one exact lexical record retrieves | ranking robustness | LOW |
| `test_zero_budget_and_record_larger_than_budget` | zero/small budgets reject tested record | all serialization boundaries | LOW |
| `test_unicode_chunking_and_content` | UTF-8 chunks preserve content and <=256 bytes | FTS normalization/casefold equivalence | MEDIUM |
| `test_binary_looking_tool_output` | escaped-looking NUL text is searchable | real arbitrary binary tool bytes | LOW |
| `test_duplicate_paths_are_canonicalized` | duplicate path strings collapse | path aliases/hard links/symlink equivalence | MEDIUM |
| `test_missing_workspace_fails_closed` | nonexistent workspace => outside scope | workspace replacement race | LOW |
| `test_sqlite_reopen_persistence` | one record persists across store reopen | corruption/crash durability | LOW |
| `test_fts_special_characters_do_not_raise` | punctuation/operators are sanitized enough not to raise for one query | Unicode/tokenizer semantic parity, 32-term truncation | MEDIUM |
| `test_task_local_and_last4_cutoff` | one foreign-task and one too-recent record excluded | all boundary steps / cross-task leakage under malformed rows | LOW |
| `test_malformed_partial_row_is_not_silently_accepted` | schema NOT NULL rejects one malformed direct insert | all malformed JSON/enum values | LOW |
| `test_concurrent_repeated_retrieval` | eight concurrent read retrievals agree | concurrent writes, DB locking, message-bus allocation | HIGH if generalized |
| `test_adversarial_near_duplicate_collapse` | one benign >=0.85 near-duplicate collapses | false-positive semantic/numeric conflict collapse | HIGH |
| `test_adversarial_outside_symlink_fails_closed` | static symlink outside workspace is rejected | retarget race inside-to-inside or inside-to-outside during hash | HIGH |
| `test_adversarial_exact_budget_boundary` | one record fits at its measured size and fails one byte below | fixed 2047/2048/2049 escape-heavy envelope cases | LOW |
| `test_provider_usage_extraction_and_invalid` | basic usage parses; completely missing usage invalidates | inconsistent total, nested cache/reasoning details, retry aggregation/provider errors | HIGH |
| `test_adversarial_fingerprint_detects_mid_read_mutation` | mutation of the already-opened inode changes fstat and becomes unstable | pathname/symlink retarget to a different inode while fd remains stable | HIGH |
| `test_malformed_json_record_is_skipped_not_crash` | malformed JSON row does not crash retrieval | silent-loss observability/accounting | LOW |

## 4. NEW ADVERSARIAL TESTS

These are genuinely new cases, not restatements of the existing fixtures.

| ID | attack | result | minimal reproduction | root cause | severity | required regression |
|---|---|---|---|---|---|---|
| A01 | duplicate candidate starvation | FAIL | unique verified target + 25 later exact keyword duplicates; query shared keywords | FTS `Q_local=20` fills with duplicates before dedup; target never reaches candidate set | HIGH | duplicates must not consume the entire candidate acquisition budget before a unique relevant record can compete |
| A02 | recency domination of old explicit error | FAIL | old `E_OLDRACE`, then 205 newer noise records; nonlexical query + `error_signature=E_OLDRACE` | error matching is only applied in newest-200 supplemental scan unless FTS query independently finds it | HIGH | explicit error/failed-command signature candidate path must find eligible old records beyond supplemental window |
| A03 | hypothesis/evidence confusion via numeric near-dedup | FAIL | old `HYPOTHESIS/UNVERIFIED: timeout 30`; newer `TEST_RESULT/VERIFIED: timeout 60 ...stopwords`; query `timeout` | `_terms` drops 2-digit numbers and stopwords; Jaccard=1; lexical RR lets concise old hypothesis score 1.1 vs verified correction 0.85; dedup discards correction | BLOCKER | contradictory numeric/value evidence must not be treated as near-duplicate; verified correction must remain eligible and dominate hypothesis |
| A04 | exact-content dedup erases outcome conflict | FAIL | identical content/command stored once FAILED and once PASSED | exact fingerprint hashes content only; metadata differences are ignored by exact dedup | MEDIUM | outcome/command/verification conflict must not silently collapse as exact duplicate |
| A05 | symlink retarget TOCTOU | FAIL | baseline link->A; during `os.read` retarget link->B while fd still reads A | pre/post `fstat(fd)` stays stable and code never re-resolves/revalidates pathname after hash; old resolved path is returned | BLOCKER | pathname/target identity must be revalidated after hashing; any retarget race must yield UNKNOWN/UNSTABLE/STALE, never FRESH |
| A06 | Unicode normalization mismatch | FAIL | record `straße`, query `STRASSE` | Python scoring uses `.casefold()` but FTS5 `unicode61` candidate generation does not provide equivalent `ß -> ss` semantics | LOW | either align candidate/scoring normalization or explicitly lock/document expected Unicode limitation |
| A07 | impossible provider total accepted | FAIL | usage `{prompt:10, completion:4, total:999}` | validity checks only nonnegative ints; no `total == input + output` invariant | BLOCKER | reject inconsistent totals unless provider-specific accounting semantics explicitly justify them |
| A08 | nested cached/reasoning audit fields lost | FAIL | `prompt_tokens_details.cached_tokens` and `completion_tokens_details.reasoning_tokens` | logger only searches top-level usage keys containing cache/reason | MEDIUM | preserve provider-native nested cache/reasoning usage fields for auditability |
| A09 | 64 MiB exact boundary | PASS | exact 64 MiB regular file then +1 byte | implementation uses `>` rather than `>=`, matching stated maximum | — | retain boundary regression |
| A10 | independent envelope boundary | PASS | constructed canonical memory messages of exactly 2047, 2048, 2049 serialized UTF-8 bytes including quotes/backslashes/newlines/non-ASCII | serializer byte count matched direct canonical JSON byte length | — | retain independent serializer boundary regression |
| A11 | multiple tool outputs + incomplete trailing step | PASS | one assistant with two tool calls/two tool outputs; later incomplete assistant | complete multi-tool step preserved; incomplete trailing assistant excluded | — | retain regression in integration suite |
| A12 | missing provider usage never falls back to local estimator | PASS | possibly-generated response with missing usage | helper returns `TOKEN_ACCOUNTING_INVALID` and no total | — | retain end-to-end provider-attempt regression |

### Scale probe

3,001 task-local records were inserted in the reviewer runtime. Approximate observations: 1.09 MiB DB, 1.98 s total insertion, 189 ms rare-old lexical retrieval. This is **not** a performance verdict because environment and thresholds are not frozen. It proves only that the existing 37 tests do not establish memory-growth/latency behavior.

## 5. BUGS FOUND

### BLOCKER

1. **A03 — verified contradictory evidence can be eliminated by near-dedup while an old unverified hypothesis survives.** This directly violates the project's hypothesis/evidence attack objective.
2. **A05 — file freshness can return `FRESH` after a symlink pathname changes target during hashing.** This contradicts the frozen fail-closed freshness requirement.
3. **A07 — token accounting accepts internally inconsistent provider totals as `OK`.** The primary metric cannot trust this path.

### HIGH

4. **A01 — duplicate flood can poison candidate acquisition before dedup.** T3's current fixture misses the failure.
5. **A02 — old explicit error/failed-strategy evidence can disappear behind the hard newest-200 supplemental window.**
6. **T6 is retrieval assistance, not loop prevention.** There is no staged proof the agent avoids the repeated failed action.

### MEDIUM

7. **A04 — content-only exact fingerprint can collapse semantically conflicting outcome metadata.**
8. **A08 — nested cached/reasoning provider fields are not preserved in structured audit fields.** Raw usage remains present, so this is not total data loss.
9. **Message-bus next-ID allocation is racy.** Two agents can independently compute the same highest+1; validation detects duplicates only after publication.
10. **`group_complete_steps` accepts every non-assistant role after an assistant until the next assistant.** This is safe only if authoritative native history shape is constrained; T10/upstream tests must prove it.

### LOW

11. **A06 — FTS5 candidate Unicode normalization and Python casefold scoring are not semantically identical.**
12. **The 32-token FTS query cap can ignore a critical term after token 32.** No direct regression exists.

## 6. TOKEN ACCOUNTING RISKS

- Missing usage for a possibly generated request correctly yields `TOKEN_ACCOUNTING_INVALID`; no local estimate substitution was found in the staging helper.
- Inconsistent totals are incorrectly accepted when all three fields are nonnegative integers. This is a primary-metric blocker.
- Nested cached/reasoning details are not promoted into `cached_fields`/`reasoning_fields`, though they remain in `raw_usage`.
- There is no authoritative integration proving every attempt, retry, parse failure, provider error, or partial response is logged exactly once.
- There is no aggregation layer in the reviewed staging helper proving failed attempts are included in experiment totals.
- Local packing units are currently structurally separate from provider usage; no path in `token_logger.py` substitutes local units. This must remain true after integration.

## 7. STALENESS RISKS

- Ordinary mutation, same-size edit, restored mtime, deletion, rename, static symlink target change, too-large, unreadable, static outside-workspace, and opened-inode mid-read mutation have dedicated fixtures.
- The demonstrated missing case is pathname identity changing while the original fd remains stable. The code compares `fstat` on the fd but does not re-resolve/re-stat the pathname and compare it to the opened object before returning `OK`.
- Hard-link and file-replacement semantics are not exhaustively tested.
- Current-state records with `STALE`/`UNKNOWN` are excluded as intended; historical errors/test results may remain labeled stale/unknown as frozen architecture permits.
- Exactly 64 MiB is accepted and 64 MiB + 1 is rejected in A09.

## 8. RETRIEVAL / DEDUP RISKS

- Candidate generation is vulnerable before ranking/dedup: FTS top-k duplicates can starve unique relevant records.
- Supplemental candidate discovery considers only the newest 200 eligible rows, so old explicit error/command matches are not guaranteed to reach scoring.
- Near-dedup uses token **sets**, discarding order, multiplicity, stopwords, and all tokens shorter than 3 characters. Numeric values such as `30` and `60` disappear entirely.
- Exact fingerprint is content-only; semantically different command/outcome/verification metadata can collapse.
- If both normalized term sets are empty, Jaccard returns 1.0, so short-token/number-only records can collapse if another signal makes them candidates.
- `unicode61` candidate normalization is not identical to Python `.casefold()` scoring normalization.
- Query candidate generation uses only the first 32 extracted FTS tokens.
- Max 2/source-step and max 8 selected records are enforced in the staged selector, but selection correctness depends on the candidate set surviving the earlier failure modes.

## 9. BASELINE / T10 RISKS

T10 has **not** been run, so no baseline-equivalence claim is acceptable.

The eventual T10 is only strong enough if memory-disabled mode proves all of the following against unpatched/native mini-SWE-agent v2.4.6 on identical deterministic fixtures:

1. no memory DB initialization or reads;
2. no fingerprint/file reads attributable to memory;
3. no retrieval calls;
4. no memory context rebuilding/copying/reordering;
5. identical system/task/native-history provider-facing message structures and ordering;
6. identical tool-call IDs, assistant/tool relationships, and tool payloads;
7. identical model, model version/provider identifier, reasoning effort, stream mode, max turns, timeout, retry rules, and tool permissions;
8. no instrumentation mutation that changes provider requests or retry behavior;
9. no synthetic memory message on empty/disabled retrieval;
10. no hidden configuration/default difference between baseline and memory-disabled condition.

A weak T10 that compares only final text, number of messages, or one happy-path trace is insufficient. Prefer fail-fast monkeypatches/counters that prove memory functions are not invoked when disabled plus exact provider-request structure comparison.

## 10. MESSAGE-BUS RISKS

The 14 current tests validate parsing, role ownership through the helper, duplicate detection, and monotonic next-ID calculation in a single-writer scenario.

`next_id()` is **not an allocator**: it scans the repository and returns highest+1 without a reservation, lock, or compare-and-swap. Two agents can both read the same state and choose the same ID. If they publish different files concurrently, the repository can temporarily contain duplicate global IDs and only later `validate()` will report the violation.

Classification: **MEDIUM correctness bug in the promised global-ID invariant**, not a core scientific-architecture defect. It can be an operational limitation only if the protocol explicitly serializes message publication through one allocator. Minimal repair: either (a) orchestrator-serialized ID assignment, or (b) optimistic HEAD/CAS publication with conflict detection and reallocation/retry. No distributed lock service is necessary.

Scientific-state conflicts remain correctly specified as stop/escalate rather than auto-resolve.

## 11. MINIMUM REQUIRED FIXES

Before authoritative integration is treated as a pass gate:

1. Make candidate acquisition duplicate-aware so repeated high-overlap rows cannot consume the entire local candidate budget before unique evidence is considered; add A01 regression.
2. Provide a bounded but non-recency-blind candidate path for explicit error/failed-command signatures; add A02 regression.
3. Repair dedup equivalence so contradictory numbers/values and material command/outcome/verification differences are not collapsed; add A03/A04 regressions. Verified contradictory evidence must never be discarded behind an old hypothesis solely due lexical compactness.
4. Revalidate pathname/target identity after hashing and fail closed on symlink/replacement races; add A05 regression.
5. Reject internally inconsistent provider usage totals and preserve provider-native cached/reasoning details; add A07/A08 regressions. End-to-end integration must count every attempt/retry/error without local-estimate fallback.
6. Add the new adversarial regressions to the canonical staging suite and rerun the exact current repository snapshot, recording command, commit, and results.
7. Treat `next-id` as advisory until publication is serialized/CAS-protected; add one deterministic race simulation to message-bus tests.
8. Only after the above, integrate into authoritative mini-SWE-agent v2.4.6 and run a strong T10 as specified. Do not touch Terminal-Bench before integration/T10/reproducibility gates pass.

Unicode normalization alignment (A06) may be documented/deferred if the architect confirms it is outside the intended identifier/error domain; it is not a core redesign requirement.

## 12. SHOULD WE PROCEED?

`FIX_THEN_INTEGRATE`

Do **not** revert v0 and do **not** redesign the core. The observed failures arise from local candidate-generation, dedup, fingerprint validation, and accounting details rather than a contradiction in the frozen high-level design.

## SELF-CHECK A — CORRECTNESS

I attempted to invalidate the findings:

- A01 remains a real failure because T3's purpose is duplicate-flood resistance; adding one unique relevant target is the minimum scenario where duplicate monopolization matters.
- A02 is not an arbitrary scale attack: the implementation explicitly caps supplemental history at 200 while the project requires recovery of old critical information and includes memory-explosion/recency attacks.
- A03 was strengthened from a generic numeric difference to the project's exact hypothesis-vs-verified-evidence requirement. The old hypothesis wins and the newer verified correction disappears from the deduped set.
- A05 changes the pathname binding, not the open fd; therefore the existing mid-read inode-mutation test cannot catch it. The returned `FRESH` classification is observably wrong for the current pathname.
- A07 does not assume provider billing semantics beyond the helper's own use of `input + output` when total is absent. If a provider legitimately defines total differently, that must be frozen/documented per provider rather than silently accepting arbitrary inconsistency.

## SELF-CHECK B — ADVERSARIAL

The new failures are attached to real stated properties rather than artificial crashes:

- duplicate flood -> retrieval poisoning/candidate starvation;
- >200 recent rows -> recency domination/old information loss;
- numeric verified correction -> hypothesis/evidence confusion;
- symlink retarget -> fail-closed current-state freshness;
- inconsistent usage -> primary-metric accounting validity.

Four new cases also passed, preventing the review from treating every untested edge as a failure.

## SELF-CHECK C — EXPERIMENT CONSISTENCY

No model, provider parameters, benchmark, task selection, primary metric, or frozen architecture was changed. Terminal-Bench was not run or inspected. No benchmark tasks/solutions were selected. The review only read source/state and executed deterministic local adversarial unit reproductions of staging logic.

## Final reviewer conclusion

The staging implementation has useful deterministic foundations, and several original fixtures likely pass exactly as reported, but the broad claims those fixtures are meant to protect do not survive hostile review. In particular, a concise old hypothesis can suppress newer verified contradictory evidence, and a symlink retarget race can allow stale current-state data to be labeled `FRESH`. Those are disqualifying for an integration-ready claim.
