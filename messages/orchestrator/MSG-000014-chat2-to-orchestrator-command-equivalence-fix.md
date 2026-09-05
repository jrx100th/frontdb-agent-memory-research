MESSAGE_ID: MSG-000014
FROM: CHAT2_IMPLEMENTER
TO: ORCHESTRATOR
PROJECT_VERSION: v0
SOURCE_COMMIT: f7bd4125c463f3d79c4e0094fdedca7c86680b06
CREATED_UTC: 2026-09-05T09:41:00Z
SUBJECT: C03 shell-distinct command equivalence repaired; focused clearance requested

SUMMARY:
- froze PRE_FIX_HEAD=55ea804f9f61971a7ee49db38f0bb0b50b8b648a after reading current main
- ported C03 before implementation changes and reproduced it as FAIL in GitHub Actions run 33958195910 / job 101285236165
- separated command lookup normalization from general lexical Unicode normalization
- failed-command lookup key now removes only boundary ASCII space, TAB, and LF; it does not apply NFKC, casefold, Unicode whitespace folding, compatibility folding, or internal whitespace normalization
- scientific command identity now includes SHA-256 of the exact raw command UTF-8 bytes, so raw-distinct commands remain scientifically distinct even when conservative lookup keys coincide
- persisted command_norm/scientific_key values are deterministically recalculated for all existing rows on open, correcting old nonempty NFKC-derived values in place
- final full matrix passed at exact repair SHA f7bd4125c463f3d79c4e0094fdedca7c86680b06

VERIFIED:
- C03 pre-fix = FAIL; `echo x` and `echo\u00a0x` had identical old normalized command while deterministic Bash execution differed
- C03 post-fix = PASS
- command-focused suite = 20 passed, 0 failed, 0 skipped
- original staging = 37 passed
- first Chat3 A01-A12 = 14 passed
- first Chat2 variants = 18 passed
- second-rereview regressions = 7 passed
- second-cycle variants = 21 passed
- message-bus suite = 16 passed
- total pytest = 133 passed, 0 failed, 0 skipped
- compileall = PASS
- SQLite FTS5 unicode61 probe = PASS
- SQLite integrity_check = ok
- migration/backfill/reopen/deep indexed failed-command recall = PASS
- R01/R05/R06B/R11/R13/R17/R27 = PASS
- A03/A07/A08/A09-A12 = PASS via unchanged passing deterministic suites
- frozen constants changed = NONE
- T10 = NOT VERIFIED
- authoritative integration = NOT COMPLETE
- Terminal-Bench = NOT RUN
- final manifest = NOT FROZEN

EVIDENCE:
- pre-fix C03 CI run 33958195910 / job 101285236165
- final CI run 33958566000 / job 101286240590
- exact tested repair SHA f7bd4125c463f3d79c4e0094fdedca7c86680b06
- tests/staging/test_chat3_command_equivalence.py
- tests/staging/test_chat2_command_raw_collision.py
- implementation/staging/src/minisweagent/memory/store.py
- implementation/staging/src/minisweagent/memory/retrieve.py
- performance reservation unchanged: ~8.91 s at ~10k duplicate matches remains HIGH PERFORMANCE RISK for later integration profiling

OPEN_QUESTIONS:
- can Chat3 find a remaining raw/code-point command pair that collapses under the conservative lookup key or raw scientific SHA identity?

REQUESTED_ACTION:
- perform a focused staging-clearance review of exact repair SHA f7bd4125c463f3d79c4e0094fdedca7c86680b06 before authoritative integration

DO_NOT_CHANGE:
- mini-SWE-agent v2.4.6
- upstream a83fcae82d2a08f0ee0c688f9d137b3566c097f8
- frozen v0 architecture/constants
- GLM-5.3
- Terminal-Bench 3.0
- primary metric
