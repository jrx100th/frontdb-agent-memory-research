# ADVERSARIAL CLEARANCE REVIEW V0

Role: `CHAT3_REVIEWER`

Review start HEAD: `5e86f4ba4c04d544f144797cb1935661bad62a19`

Exact tested repair HEAD: `bde837617f53d4655b88c8dcb48c6656d77ca0dc`

Independent reviewer evidence branch: `chat3/clearance-review-20260905`

Independent reviewer CI: run `33952778470`, job `101270523930`

Terminal-Bench was not run or inspected. No production/staging implementation, frozen architecture, benchmark configuration, provider configuration, task selection, or primary metric was modified by Chat3.

## 1. VERDICT

`FAIL`

Recommendation: `FIX_THEN_REREVIEW`.

All seven defects that survived the previous rereview (R01/R05/R06B/R11/R13/R17/R27) now survive their intended structural re-attacks. Chat2's `113/113` CI claim is genuine at the exact repair SHA, and current main is implementation-equivalent to that tested SHA.

However, the clearance review found one new **HIGH correctness defect** adjacent to R05: command normalization uses NFKC for both indexed failed-command lookup and scientific dedup equivalence. NFKC can map shell-distinct command strings to the same normalized command. A concrete exact-repository reproducer using `echo\u00a0x` (NBSP) versus `echo x` caused one record to disappear from candidate acquisition because both commands receive the same `command_norm` / scientific equivalence key. In bash these are materially different: `echo x` executes normally while `echo<NBSP>x` is parsed as a different command token and fails command lookup.

Because this can erase distinct failed-command evidence before ranking, it threatens evidence integrity and retrieval correctness. Under the stated clearance standard it is a HIGH correctness defect and staging is not yet cleared for authoritative integration.

This is not a core contradiction. A conservative local repair to command representation/equivalence is sufficient; no v0 redesign is justified.

## 2. EXACT TARGET / CI AUDIT

### Current-main equivalence

Compare `bde837617f53d4655b88c8dcb48c6656d77ca0dc` -> `5e86f4ba4c04d544f144797cb1935661bad62a19` changed only:

- `agents/chat2_implementer/LAST_SEEN`
- `messages/chat3_reviewer/MSG-000011-chat2-to-chat3-second-rereview-request.md`
- `messages/orchestrator/MSG-000010-chat2-to-orchestrator-second-rereview-fixes.md`

No implementation, staging-test, state, manifest, or architecture file changed after the tested repair SHA. Therefore Chat2's final CI is valid evidence for the current experimental implementation bits.

### Chat2 CI

Run `33951595016`, job `101267310002`:

- `head_sha = bde837617f53d4655b88c8dcb48c6656d77ca0dc`
- status: completed
- conclusion: success
- exact checkout confirmed in logs

The workflow actually executed:

- original staging suite: `37 passed`
- first Chat3 A01-A12 regressions: `14 passed`
- first Chat2 repair variants: `18 passed`
- second-rereview seven regressions: `7 passed`
- second-cycle neighboring variants: `21 passed`
- message-bus suite: `16 passed`

Total: `113 passed, 0 failed, 0 skipped` across the requested pytest suites, followed by compileall PASS, FTS5 PASS, and SQLite `integrity_check=ok`.

Classification: **113/113 = VERIFIED**.

## 3. PREVIOUS SEVEN DEFECTS

| ID | clearance result | evidence |
|---|---|---|
| R01 duplicate acquisition starvation | PASS | exact-equivalence SQL grouping removes the 4096-row correctness cliff; 10k/12k committed floods pass; independent C01/C02 preserve scientifically distinct groups and unique targets |
| R05 deep failed-command whitespace mismatch | PASS for the intended trim/backfill defect | leading/trailing whitespace, tabs/newline suffix, deep indexed recall and realistic old-schema reopen/backfill pass; a separate NFKC command-equivalence defect was found and is the clearance blocker |
| R06B signature substring false positive | PASS | contiguous normalized token matching rejects `E_SIG_EXTRA` for `E_SIG`, `ABC_10` for `ABC_1`; independent C07-C09 cover suffix/contiguity/punctuation behavior |
| R11 file-state evidence collapse | PASS | scientific equivalence includes canonical file paths/fingerprints; independent reordered-equivalent, changed-SHA and missing-vs-existing variants behave correctly |
| R13 symlink ABA freshness | PASS | pre/post lstat mode/dev/ino/size/mtime/ctime/raw-link target + resolved path/opened-file checks fail closed for observable mutations; independent repeated ABA had 50/50 non-OK |
| R17 old normalized Unicode recall | PASS | indexed NFKC+casefold shadow is supplemental and task-local; >3000 mixed Unicode/ASCII and task-isolation variants pass |
| R27 supplemental candidate monopoly | PASS | supplemental admissions capped at 10; independent source-composition tests preserve ordinary local/task candidates and still allow explicit failure evidence |

## 4. NEW ADVERSARIAL TESTS

Chat3 created reviewer-only exact-repository tests on branch `chat3/clearance-review-20260905` and executed them with GitHub Actions run `33952778470`, job `101270523930`.

Result: **22 total: 21 PASS / 1 FAIL**.

| ID | attack | result | why it matters |
|---|---|---|---|
| C01 | 5000 exact duplicates plus VERIFIED scientific variant plus unique target | PASS | scientific grouping does not erase verification-distinct evidence or unique evidence |
| C02 | exact duplicates across many source steps plus unique target | PASS | duplicate source steps group without candidate starvation |
| C03 | `echo<NBSP>x` versus `echo x`, otherwise identical failure evidence | **FAIL** | NFKC maps shell-distinct commands to the same command/scientific key; one record is erased before ranking |
| C04 | internal double-space command versus single-space failed-command signature | PASS | internal shell whitespace is not collapsed by trim logic |
| C05 | realistic pre-derived schema migration, reopen twice, then deep command recall | PASS | valid populated staging DB migration is deterministic, idempotent and searchable |
| C06 | malformed legacy JSON row | PASS as fail-loud probe | migration raises rather than silently manufacturing derived state; corrupted DB can still block startup |
| C07 | `ABC_1` versus `ABC_10` | PASS | suffix substring false positive is rejected |
| C08 | non-contiguous versus contiguous multi-token signature | PASS | multi-token explicit signature requires contiguous token sequence |
| C09 | `ERR-42` queried as `ERR 42` | PASS | punctuation-tokenized signature behavior is deterministic |
| C10 | same files/state with reversed file-path order | PASS | benign reordered representation still deduplicates |
| C11 | same two-file set with one SHA changed | PASS | material file-state change remains distinct |
| C12 | missing versus existing referenced file | PASS | materially different file status remains distinct |
| C13 | symlink inside -> outside -> inside during hash | PASS | observable containment ABA fails closed |
| C14 | rename/recreate same-size file with restored mtime | PASS | replacement remains non-OK despite size/mtime restoration |
| C15 | symlink -> regular -> symlink ABA | PASS | path-type mutation fails closed |
| C16 | 50 rapid A -> B -> A symlink ABA runs | PASS | `0/50` returned OK/FRESH-capable |
| C17 | old mixed `Straße_ID42` / `STRASSE_id42` beyond 3000 rows | PASS | indexed normalized shadow is not newest-200 dependent |
| C18 | normalized Unicode equivalent in foreign task | PASS | normalized shadow remains task-local |
| C19 | 20 local + 10 task + 100 explicit candidates | PASS | final pool <=40, supplemental <=10, ordinary sources preserved |
| C20 | explicit failure with full ordinary candidate supply | PASS | fairness repair does not starve explicit failure evidence in reverse |
| C21 | VERIFIED numeric correction after second-cycle changes | PASS | earlier hypothesis/evidence fix remains intact |
| C22 | additive/mismatched/missing provider usage spot check | PASS | token accounting remains fail-closed |

### C03 minimal reproduction

Raw commands:

- `echo x`
- `echo\u00a0x` where `\u00a0` is NO-BREAK SPACE

They are not the same byte/string command and are shell-distinct. Yet `_normalize_command()` applies NFKC then `.strip()`, so both normalize to `echo x`. `_scientific_key()` includes this normalized value; retrieval exact-equivalence grouping therefore treats otherwise identical records as one scientific class. The exact GitHub Actions reviewer run observed candidate IDs `{2}` where both `{1,2}` were required.

Severity: **HIGH correctness**.

Required regression: commands that are distinct under shell parsing must not be merged solely by Unicode compatibility normalization. The fix should remain conservative: representation noise such as leading/trailing transport whitespace can normalize, but the scientific-equivalence key must preserve shell-significant command differences.

## 5. FRESHNESS CLEARANCE

A05/R13 is cleared for staging.

Independent attacks covered:

- A -> B -> A symlink ABA
- inside -> outside -> inside
- rename/recreate
- same-size replacement with restored mtime
- symlink -> regular -> symlink
- rapid repeated ABA

Independent repeated ABA result: `50 runs / 0 OK`.

The implementation now compares observable path-entry metadata (`mode/dev/ino/size/mtime_ns/ctime_ns`), raw symlink target, resolved target, workspace containment, opened-file identity and pre/post fd stability. No real observable mutation returning FRESH was reproduced.

Theoretically invisible OS mutations are not treated as a failure; the documented observable fail-closed contract is the staging requirement.

## 6. SCHEMA / MIGRATION REVIEW

`PASS` for valid staged databases.

A realistic database with the old `memories` schema and populated `memories_fts` was opened by the new `MemoryStore`. Migration:

1. added `command_norm`, `search_norm`, and `scientific_key`;
2. created the current indexes and normalized FTS table/triggers;
3. backfilled derived fields;
4. rebuilt normalized FTS when needed;
5. reopened idempotently with stable derived values/counts;
6. successfully served indexed deep failed-command recall afterward.

Residual robustness issue: malformed legacy JSON in `file_paths`/`file_fingerprints` raises during backfill and can block startup. This is fail-loud rather than silent scientific corruption, and prior staged writers produce valid JSON. Classification: LOW/MEDIUM robustness reservation, not a staging-clearance correctness blocker.

## 7. PERFORMANCE REVIEW

Classification: **HIGH PERFORMANCE RISK**, not a correctness blocker.

Chat2 measured approximately `8.91 s` for 10,001 matching rows producing two final candidates. The new exact-grouping query is finite and database-bounded, and there is no frozen latency gate. It removes the previous correctness boundary, but the SQL window over all matches plus paginated retrieval can be expensive on adversarial large-match histories.

No unbounded loop or concrete benchmark timeout violation was demonstrated. Therefore this observation does not independently block staging clearance, but integration profiling must measure retrieval latency and history growth before benchmark authorization.

## 8. PRESERVED CLEARED LOGIC

Spot checks found no second-cycle regression in:

- A03 newer VERIFIED contradiction handling;
- A07 additive provider total consistency / fail-closed malformed usage;
- A08 raw/nested cache and reasoning audit preservation;
- A09 64 MiB boundary (covered by unchanged prior CI);
- A10 whole serialized 2048-unit memory envelope (covered by unchanged prior CI);
- A11 complete native step grouping (covered by unchanged prior CI);
- A12 missing provider usage -> `TOKEN_ACCOUNTING_INVALID` (spot-checked independently).

Provider-attempt interception/aggregation and GLM/TokenRouter response mapping remain integration gates, not staging claims.

## 9. FROZEN-CONSTANT AUDIT

`PASS`.

No change was found to the frozen v0 architecture/constants:

- mini-SWE-agent v2.4.6 / upstream `a83fcae82d2a08f0ee0c688f9d137b3566c097f8`;
- recent steps = 4;
- retrieval budget = 2048 whole-message local units;
- max chunk = 256;
- max selected records = 8;
- Q_local = 20;
- Q_task = 10;
- candidate_pool_max = 40;
- near-dedup Jaccard threshold = 0.85;
- ranking weights unchanged;
- primary FTS5 = `unicode61`;
- zero extra LLM calls;
- task-local memory;
- GLM-5.3;
- Terminal-Bench 3.0;
- primary metric = provider-reported total tokens / successful tasks.

New internal implementation controls such as supplemental candidate limit 10 and FTS page size 256 do not alter the published scoring/budget constants, but their performance must remain observable during integration.

## 10. CLAIM AUDIT

| claim | classification |
|---|---|
| current main implementation equals tested repair SHA | VERIFIED |
| Chat2 `113/113` matrix | VERIFIED |
| R01 fixed | VERIFIED |
| R05 original whitespace/deep-recall defect fixed | VERIFIED |
| R06B fixed | VERIFIED |
| R11 fixed | VERIFIED |
| R13 fixed | VERIFIED |
| R17 fixed | VERIFIED |
| R27 fixed | VERIFIED |
| command normalization is safe scientific equivalence | FALSE |
| staging cleared for authoritative integration | FALSE |
| token accounting ready for integration testing | SUPPORTED_BUT_NOT_VERIFIED end-to-end |
| baseline safe | UNVERIFIED — T10 not run |
| benchmark ready | FALSE — integration/T10/upstream/provider/reproducibility/final-manifest gates remain open |

## 11. REMAINING RISKS

### HIGH correctness — blocks clearance

- NFKC command normalization can collapse shell-distinct failed-command evidence before ranking and can make failed-command retrieval treat distinct command strings as equivalent.

### Reservations — do not independently block clearance

- high performance risk for very large same-term FTS match sets (~8.91 s observed at 10k matches);
- malformed/corrupted legacy JSON can fail migration startup loudly;
- actual GLM/TokenRouter attempt capture/aggregation remains unintegrated;
- T10, upstream tests, authoritative integration and final manifest remain open.

## 12. FINAL RECOMMENDATION

`FIX_THEN_REREVIEW`

Do not begin authoritative mini-SWE-agent integration yet. Chat2 should make one local command-equivalence repair that preserves shell-significant Unicode/code-point distinctions while still handling intended leading/trailing representation noise, add the C03 regression and nearby compatibility-character controls, run the full deterministic matrix at one exact repair SHA, and return that SHA for a focused Chat3 clearance check.

No core redesign or v0 revert is justified.

## SELF-CHECK A — CORRECTNESS

I attempted to falsify the new failure. The two command strings are not merely visually different: actual bash behavior differs (`echo x` succeeds; the NBSP-containing command is treated as a different command token and fails lookup). The failure is caused before scoring by the exact implementation path: NFKC command normalization feeds the scientific key/equivalence grouping.

I did not convert the 8.91 s performance observation into a blocker because no frozen latency threshold or demonstrated timeout violation exists.

## SELF-CHECK B — ADVERSARIAL

Twenty-one of twenty-two new variants passed. All seven previously surviving defects passed structural re-attacks. The clearance failure is therefore narrow rather than a blanket rejection or a demand for endless edge-case work.

The failing case directly exercises the user's requested safety condition: commands that normalize similarly must not be merged when shell semantics can differ.

## SELF-CHECK C — EXPERIMENT CONSISTENCY

Chat3 changed no staging/production implementation, model, architecture constant, benchmark, task selection, provider parameter, or primary metric. Reviewer code exists only on the reviewer evidence branch. Terminal-Bench was not run or inspected. The durable main-branch writes are limited to this report, one reviewer message, and Chat3's own LAST_SEEN pointer.