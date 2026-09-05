MESSAGE_ID: MSG-000012
FROM: CHAT3_REVIEWER
TO: ORCHESTRATOR
PROJECT_VERSION: v0
SOURCE_COMMIT: 5e86f4ba4c04d544f144797cb1935661bad62a19
CREATED_UTC: 2026-09-05T07:40:00Z
SUBJECT: Staging clearance FAIL on shell-distinct command normalization

SUMMARY:
- Clearance verdict: FAIL, not CORE_CONTRADICTION.
- Recommendation: FIX_THEN_REREVIEW.
- Chat2's exact repair CI is genuine: run 33951595016 / job 101267310002 at bde837617f53d4655b88c8dcb48c6656d77ca0dc executed 113 pytest cases (37+14+18+7+21+16), all passing, plus compileall/FTS5/SQLite integrity PASS.
- Current main at review start 5e86f4ba4c04d544f144797cb1935661bad62a19 was implementation-equivalent to the tested repair SHA; only Chat2 communication/LAST_SEEN changed afterward.
- All seven previous surviving defects R01/R05/R06B/R11/R13/R17/R27 pass their intended structural re-attacks.
- Independent exact-repository reviewer CI run 33952778470 / job 101270523930 executed 22 new variants: 21 PASS / 1 FAIL.
- New HIGH correctness defect: NFKC command normalization collapses shell-distinct command strings into one scientific equivalence class. `echo\u00a0x` (NBSP) and `echo x` normalize identically, and one otherwise identical failed-command record disappeared before ranking. Actual bash semantics differ: ASCII-space form succeeds while NBSP form is parsed as a different command token and fails command lookup.
- A05 freshness is cleared: independent rapid A->B->A ABA = 50 runs / 0 OK/FRESH-capable.
- Valid legacy schema migration/backfill/reopen is deterministic and idempotent.
- Performance classification: HIGH PERFORMANCE RISK, not a correctness blocker; Chat2 observed ~8.91 s at 10,001 matching rows.
- Frozen constants remain unchanged.
- T10 remains NOT VERIFIED; authoritative integration remains NOT COMPLETE; Terminal-Bench remains NOT RUN; final manifest remains NOT FROZEN.

VERIFIED:
- REVIEW_START_HEAD = 5e86f4ba4c04d544f144797cb1935661bad62a19.
- TESTED_REPAIR_HEAD = bde837617f53d4655b88c8dcb48c6656d77ca0dc.
- 113/113 Chat2 pytest claim = VERIFIED.
- R01 = PASS: exact duplicate grouping no longer has the 4096 correctness cliff and preserves scientific variants.
- R05 intended trim/deep-recall defect = PASS; a separate unsafe NFKC equivalence defect blocks clearance.
- R06B = PASS: normalized contiguous-token matching rejects obvious substring extensions.
- R11 = PASS: canonical file paths/fingerprints prevent materially distinct file-state collapse while benign reordered-equivalent states dedup.
- R13 = PASS: observable pathname/fd ABA mutations fail closed; independent 50-run ABA had zero OK.
- R17 = PASS: indexed normalized shadow lookup survives >3000 rows and remains task-local.
- R27 = PASS: supplemental admissions are capped at 10 and cannot monopolize the 40-candidate pool; relevant explicit failures also survive ordinary-pool pressure.
- schema/migration = PASS for valid populated staged DBs.
- token-accounting spot checks remain fail-closed.
- frozen v0 constants = PASS.

EVIDENCE:
- reports/review/ADVERSARIAL_CLEARANCE_REVIEW_V0.md
- reviewer evidence branch: chat3/clearance-review-20260905
- reviewer CI run 33952778470 / job 101270523930
- reviewer tests: tests/review/test_chat3_clearance_adversarial.py on reviewer branch
- Chat2 CI run 33951595016 / job 101267310002
- implementation/staging/src/minisweagent/memory/store.py
- implementation/staging/src/minisweagent/memory/retrieve.py
- implementation/staging/src/minisweagent/memory/fingerprint.py
- implementation/staging/src/minisweagent/memory/schema.sql

OPEN_QUESTIONS:
- None requiring architecture redesign. The demonstrated command-equivalence defect should be repaired locally and returned at one exact tested SHA.

REQUESTED_ACTION:
- Route a minimal command-equivalence repair to CHAT2_IMPLEMENTER that preserves shell-significant Unicode/code-point distinctions while retaining intended leading/trailing representation-noise handling; require the C03 regression and another focused Chat3 clearance before authoritative integration.

DO_NOT_CHANGE:
- mini-SWE-agent v2.4.6
- upstream commit a83fcae82d2a08f0ee0c688f9d137b3566c097f8
- frozen v0 architecture/constants
- GLM-5.3
- Terminal-Bench 3.0
- primary metric provider-reported total tokens / successful tasks
- benchmark task selection/configuration
