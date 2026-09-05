# COMMAND EQUIVALENCE CLEARANCE V0

Role: `CHAT3_REVIEWER`

Review start HEAD: `235d1308c6271e22cf5dd36e27e259f5a36b46b1`

Exact tested repair HEAD: `f7bd4125c463f3d79c4e0094fdedca7c86680b06`

Independent reviewer evidence branch: `chat3/final-command-clearance-20260905`

Independent reviewer CI: run `33959539227`, job `101288875042`

No Terminal-Bench task was run or inspected. Chat3 did not modify staging/production implementation, architecture, state, manifests, provider configuration, benchmark selection, or primary metric.

## 1. VERDICT

`PASS_WITH_RESERVATIONS`

Recommendation: `PROCEED_TO_AUTHORITATIVE_INTEGRATION`.

The single HIGH correctness defect from the prior staging-clearance review (C03, NFKC collapsing shell-distinct command evidence) is repaired. Independent focused attacks found no new HIGH/BLOCKER correctness defect in command identity, lookup normalization, lookup collisions, migration/backfill, task isolation, scientific dedup, or the previously cleared staging defects.

The existing ~8.91 s / ~10k lexical-match observation remains a `HIGH PERFORMANCE RISK` to profile during authoritative integration, but it is not a staging correctness blocker because no frozen latency threshold, unbounded loop, or demonstrated timeout incompatibility exists.

## 2. EXACT TARGET AUDIT

At review start, `main = 235d1308c6271e22cf5dd36e27e259f5a36b46b1`.

Compare `f7bd4125c463f3d79c4e0094fdedca7c86680b06 -> 235d1308c6271e22cf5dd36e27e259f5a36b46b1` changed only:

- `agents/chat2_implementer/LAST_SEEN`
- `messages/chat3_reviewer/MSG-000015-chat2-to-chat3-command-equivalence-clearance-request.md`
- `messages/orchestrator/MSG-000014-chat2-to-orchestrator-command-equivalence-fix.md`

No file changed after the tested SHA under:

- `implementation/staging/`
- `tests/staging/`
- `state/`
- `architecture/`
- `manifests/`

Therefore current-main experimental implementation bits are equivalent to the exact tested repair SHA.

## 3. CHAT2 CI AUDIT

Run `33958566000`, job `101286240590`:

- `head_sha = f7bd4125c463f3d79c4e0094fdedca7c86680b06`
- status = completed
- conclusion = success
- checkout log explicitly prints the exact tested SHA

Actual executed pytest suites/results:

| suite | result |
|---|---:|
| original staging | 37 passed |
| first Chat3 A01-A12 | 14 passed |
| first Chat2 variants | 18 passed |
| second-rereview regressions | 7 passed |
| second-cycle variants | 21 passed |
| command-equivalence regressions | 20 passed |
| message-bus tests | 16 passed |
| **TOTAL** | **133 passed** |

The same job then ran compileall successfully, SQLite FTS5 `unicode61` probe successfully, and `PRAGMA integrity_check = ok`.

Classification: **133/133 = VERIFIED**.

## 4. C03 RE-ATTACK

`PASS`.

Independent reviewer test F01 used the exact pair:

- `echo x`
- `echo\u00a0x` (NBSP)

The test executed both under `bash --noprofile --norc -c` and verified different shell behavior (`echo x` succeeds; the NBSP form does not execute as the same command), different lookup keys, different raw UTF-8 SHA-256 identities, different scientific keys, and coexistence of both records in end-to-end candidate acquisition.

The repair no longer applies NFKC/casefold/Unicode-space folding to the failed-command lookup key.

## 5. RAW COMMAND SCIENTIFIC IDENTITY

`PASS`.

`_scientific_key()` now includes both the conservative command lookup key and `SHA256(exact raw command UTF-8 bytes)`. `_dedup_equivalent()` also requires equal raw-command SHA before considering two records equivalent.

Independent attacks verified raw-distinct scientific identity for:

- NBSP and other Unicode whitespace;
- canonical-composed versus decomposed Unicode;
- zero-width codepoints;
- internal newline versus ASCII space;
- CR/VT/FF boundary controls;
- escaped trailing ASCII space versus bare trailing backslash;
- multiple boundary-ASCII representations sharing one lookup key;
- single-quote versus double-quote forms;
- shell metacharacter/backslash differences.

No raw-distinct pair was destructively scientifically deduplicated.

## 6. LOOKUP NORMALIZATION

`PASS`.

The implementation uses `value.strip(" \t\n")` for the persisted failed-command lookup key. It does not NFKC-normalize, casefold, fold Unicode whitespace, or change internal codepoints/whitespace.

The committed matrix plus independent reviewer attacks verified:

- leading/trailing ASCII SPACE/TAB/LF normalize as intended;
- NBSP, IDEOGRAPHIC SPACE, NARROW NBSP, EM SPACE, FIGURE SPACE remain distinct;
- CR, vertical tab and form feed remain distinct;
- internal TAB/SPACE/newline distinctions remain preserved;
- Unicode normalization forms remain distinct;
- zero-width characters remain distinct;
- quoting, metacharacters and backslash differences remain distinct.

When uncertain, the lookup key now preserves distinction.

## 7. LOOKUP COLLISION VS RAW IDENTITY

`PASS`.

Two stronger reviewer attacks deliberately created lookup collisions.

1. Five boundary-ASCII variants of `pytest x` all produced the same lookup key while producing five different raw SHA/scientific identities. All five remained candidates and selected evidence.
2. A shell-significant escaped trailing-space command and a bare trailing-backslash command produced different Bash output but the same boundary-trimmed lookup key. Both remained scientifically distinct and both survived SQL grouping, candidate acquisition, near dedup and final selection.

This directly tests the intended safety architecture: lookup collisions are allowed; raw scientific identity prevents destructive evidence collapse.

## 8. MIGRATION / BACKFILL

`PASS`.

Independent tests forced existing persisted rows back to the previous NFKC-derived `command_norm` and previous scientific-key rule, including an NBSP/ASCII collision. Opening the database with the repaired `MemoryStore`:

- recalculated all persisted command lookup keys;
- recalculated all scientific keys using exact raw-command SHA;
- separated old NBSP/ASCII scientific collisions;
- preserved `idx_memories_task_command_norm` and `idx_memories_task_scientific_key`;
- passed SQLite integrity check;
- preserved deep indexed failed-command retrieval after more than the recent supplemental window;
- reopened idempotently without semantic changes.

A second migration test verified raw-distinct boundary-ASCII variants may intentionally share `command_norm` but retain distinct scientific keys and both remain retrievable.

The previously documented malformed-legacy-JSON fail-loud behavior was not worsened and remains a robustness reservation only.

## 9. NEW FOCUSED ADVERSARIAL TESTS

Reviewer-only exact-repository CI run `33959539227`, job `101288875042` executed **21 new pytest cases: 21 PASS / 0 FAIL**.

| ID | attack | result | severity if failed |
|---|---|---|---|
| F01 | exact C03 NBSP vs ASCII shell behavior + end-to-end noncollapse | PASS | HIGH |
| F02 | five Unicode boundary-whitespace codepoints must not strip | PASS (5 cases) | HIGH |
| F03 | NFC-equivalent composed/decomposed command bytes | PASS | HIGH |
| F04 | zero-width codepoint preservation | PASS | HIGH |
| F05 | internal newline vs space | PASS | HIGH |
| F06 | CR/VT/FF boundary controls must remain distinct | PASS (3 cases) | HIGH |
| F07 | shell-significant escaped trailing-space lookup collision | PASS | HIGH |
| F08 | five raw-distinct allowed boundary variants share lookup but not scientific identity | PASS | HIGH |
| F09 | single-quote vs double-quote equal-output commands | PASS | HIGH |
| F10 | shell metacharacter/backslash difference | PASS | HIGH |
| F11 | previous NFKC collision migration + idempotent reopen | PASS | HIGH |
| F12 | migration with intentional new lookup collision + scientific separation | PASS | HIGH |
| F13 | deep indexed lookup after migration beyond recent window | PASS | HIGH |
| F14 | failed-command task isolation | PASS | BLOCKER/HIGH |
| F15 | general NFKC lexical shadow remains separate from command lookup | PASS | HIGH |

The reviewer CI also reran the committed 20 command-equivalence cases and 21 previously-cleared Chat3 retrieval/freshness cases; both groups passed in full. Compileall also passed.

## 10. PREVIOUSLY CLEARED REGRESSIONS

`PASS`.

Focused reviewer CI reran:

- `tests/staging/test_chat3_second_rereview.py` (7 cases)
- `tests/staging/test_chat3_adversarial.py` (14 cases)

Result: `21 passed`.

This rechecks the command-adjacent/retrieval/freshness path without reopening unrelated low-value edge hunting. The full Chat2 133-case matrix independently supplies additional unchanged regression evidence for R01/R05/R06B/R11/R13/R17/R27 and A03/A07/A08/A09-A12.

No command repair-induced HIGH/BLOCKER regression was found.

## 11. FROZEN CONSTANTS

`PASS`.

The repair diff from pre-fix to tested repair changed only `store.py`, four lines of `retrieve.py`, reviewer/implementer command tests, and a CI workflow. No architecture/state/manifest file changed.

Frozen values remain:

- mini-SWE-agent `v2.4.6`;
- upstream `a83fcae82d2a08f0ee0c688f9d137b3566c097f8`;
- recent steps `4`;
- retrieval budget `2048` whole serialized memory units;
- max chunk `256`;
- FTS5 `unicode61`;
- zero extra LLM calls;
- task-local memory / cross-task disabled;
- no embeddings/vector DB;
- GLM-5.3;
- Terminal-Bench 3.0;
- primary metric = provider-reported total tokens / successful tasks.

The previously frozen retrieval constants/ranking path were not altered by this narrow repair.

## 12. PERFORMANCE / RESERVATIONS

Performance classification remains **HIGH PERFORMANCE RISK** and is carried forward.

The prior ~8.91 s observation at ~10k duplicate lexical matches is not changed by this command-equivalence patch and is not a staging correctness failure. Authoritative integration must profile retrieval latency under realistic mini-SWE-agent history growth and enforce the integration/runtime gates before benchmark authorization.

Other carried reservations:

- malformed legacy JSON can fail migration startup loudly; this is fail-loud robustness rather than silent scientific corruption;
- failed-command lookup is intentionally coarser than raw scientific identity for boundary ASCII noise, so lookup collisions are possible, but the reviewer verified raw distinct records survive those collisions end-to-end;
- provider-attempt accounting aggregation and actual GLM/TokenRouter usage-shape mapping remain integration gates;
- T10 baseline equivalence remains unverified.

None is a demonstrated HIGH/BLOCKER staging correctness defect under this review's clearance standard.

## 13. SELF-CHECKS

### A — Correctness

Attempted to falsify the PASS by using shell-distinct commands that still collide under the allowed boundary-trim rule. Both raw records survived candidate acquisition and final selection, validating that the raw-SHA identity barrier—not assumptions about shell equivalence—is carrying scientific safety.

### B — Adversarial

Tests went beyond Chat2 fixtures: extra Unicode whitespace/control characters, normalization forms, zero-width characters, shell-significant escaped boundary space, multi-record lookup collisions, task isolation and forced previous-derived-value migration. No generalization failure was found.

### C — Experiment consistency

Chat3 changed no model/provider/benchmark/frozen architecture/primary metric/task selection. Terminal-Bench was not run or inspected. Reviewer-only branch changes consist solely of tests/workflow evidence.

## 14. FINAL RECOMMENDATION

`PROCEED_TO_AUTHORITATIVE_INTEGRATION`.

This authorizes only the next controlled gate:

- integrate into exact mini-SWE-agent v2.4.6 at upstream `a83fcae82d2a08f0ee0c688f9d137b3566c097f8`;
- implement `memory_enabled=false` native bypass;
- run integrated T1-T10 and strong T10 exact baseline equivalence;
- run upstream regression tests;
- integrate provider-attempt usage capture and validate GLM/TokenRouter usage shape;
- profile retrieval latency/history growth.

**It does not authorize Terminal-Bench.** Terminal-Bench remains forbidden until the later integration/T10/reproducibility gates pass.
