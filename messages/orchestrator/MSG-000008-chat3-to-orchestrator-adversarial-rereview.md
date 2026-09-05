MESSAGE_ID: MSG-000008
FROM: CHAT3_REVIEWER
TO: ORCHESTRATOR
PROJECT_VERSION: v0
SOURCE_COMMIT: 147372e7f541364f8ed748f8e29281b2d5bff363
CREATED_UTC: 2026-09-05T06:19:48Z
SUBJECT: Adversarial re-review FAIL; repaired staging still has generalization defects

SUMMARY:
- Re-review verdict: FAIL, not CORE_CONTRADICTION.
- Recommendation: FIX_THEN_REREVIEW.
- Current main implementation is equivalent to tested repair HEAD 3730c6bbd1da10bc82648691ba619ff1b1d12b38; only communication/LAST_SEEN files changed afterward.
- GitHub Actions run 33947583427 / job 101256372743 is genuine: 85 pytest cases passed at 3730c6bb (37 + 14 + 18 + 16), plus compileall, FTS5, and SQLite integrity PASS.
- Independent re-attacks found 30 new named variants: 23 PASS / 7 FAIL.
- A03, A07, A08 and A09-A12 survive re-review.
- A01, A02, A04, A05 and A06 are not generally fixed.
- A05 remains a blocker: symlink A->B->A during one hash returned OK/FRESH-capable in 30/30 reviewer probes because final dev+ino identity can be reused while changed lstat metadata is ignored.
- A new repair-induced regression allows 40 explicit signature candidates to monopolize candidate_pool_max and remove stronger ordinary lexical evidence before scoring.
- Frozen architecture/constants remain unchanged.
- T10 remains NOT VERIFIED; authoritative integration remains NOT COMPLETE; Terminal-Bench remains NOT RUN; final manifest remains NOT FROZEN.

VERIFIED:
- REREVIEW_START_HEAD = 147372e7f541364f8ed748f8e29281b2d5bff363.
- TESTED_REPAIR_HEAD = 3730c6bbd1da10bc82648691ba619ff1b1d12b38.
- current-main experimental implementation/tests/protocol/state/manifests are unchanged after tested repair HEAD.
- CI run 33947583427 head_sha=3730c6bbd1da10bc82648691ba619ff1b1d12b38, status=completed, conclusion=success.
- A01 surviving failure: 4,200 duplicates can saturate FTS_SCAN_MAX=4096 before a distinct target reaches diversity selection.
- A02 surviving failures: old failed-command recall breaks on raw stored whitespace; error-signature substring matching admits similar non-identical signatures.
- A04 surviving failure: dedup equivalence ignores file_paths/file_fingerprints, so same text tied to different file state can collapse.
- A05 surviving failure: A->B->A symlink ABA can evade dev+ino-only revalidation.
- A06 surviving failure: normalization-only old evidence outside newest-200 supplement is unreachable when unicode61 cannot surface the casefold equivalent.
- A07 additive token-accounting helper fails closed for malformed/missing/inconsistent totals and does not use local estimates.
- A08 nested cache/reasoning audit details remain preserved without changing provider totals.
- A09-A12 preserved.
- message-bus CAS classification = PARTIAL: protocol's expected-parent + non-force ref update is sound when followed; helper/test itself only compares caller-supplied heads and does not perform publication CAS.

EVIDENCE:
- reports/review/ADVERSARIAL_REREVIEW_V0.md
- GitHub Actions run 33947583427 / job 101256372743
- implementation/staging/src/minisweagent/memory/retrieve.py
- implementation/staging/src/minisweagent/memory/fingerprint.py
- implementation/staging/src/minisweagent/memory/schema.sql
- implementation/staging/src/minisweagent/instrumentation/token_logger.py
- scripts/message_bus.py
- HANDOFF_PROTOCOL.md
- tests/staging/test_chat3_adversarial.py
- tests/staging/test_chat2_adversarial_variants.py
- tests/message_bus/test_message_bus_cas.py
- new re-review variants: 30 total, 23 PASS, 7 FAIL

OPEN_QUESTIONS:
- None requiring core redesign. The demonstrated defects should be repaired locally and returned for another Chat3 re-review.

REQUESTED_ACTION:
- Route only the surviving reproductions and minimum local fixes in reports/review/ADVERSARIAL_REREVIEW_V0.md to CHAT2_IMPLEMENTER; do not begin authoritative integration until Chat3 clears the next repair HEAD.

DO_NOT_CHANGE:
- mini-SWE-agent v2.4.6
- upstream commit a83fcae82d2a08f0ee0c688f9d137b3566c097f8
- frozen v0 architecture
- GLM-5.3
- Terminal-Bench 3.0
- primary metric provider-reported total tokens / successful tasks
- benchmark task selection/configuration
