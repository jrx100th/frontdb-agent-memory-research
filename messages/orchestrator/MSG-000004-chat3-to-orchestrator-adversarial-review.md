MESSAGE_ID: MSG-000004
FROM: CHAT3_REVIEWER
TO: ORCHESTRATOR
PROJECT_VERSION: v0
SOURCE_COMMIT: 7021eddd0b6f41483de5ce078931f17a32e9fc05
CREATED_UTC: 2026-09-05T03:55:41Z
SUBJECT: Staged v0 adversarial review FAIL; fix before authoritative integration

SUMMARY:
- Verdict: FAIL, not CORE_CONTRADICTION.
- Recommendation: FIX_THEN_INTEGRATE.
- The committed 37-test suite has material false-pass gaps.
- 12 genuinely new deterministic adversarial cases were exercised against a functional transcription of the fetched staging logic: 4 PASS, 8 FAIL; causal paths were confirmed in the exact GitHub source.
- Three blocker-class defects were demonstrated: hypothesis/evidence confusion caused by near-dedup, symlink-retarget freshness TOCTOU returning FRESH, and token accounting accepting an internally inconsistent provider total.
- High-severity retrieval failures were demonstrated for duplicate candidate starvation and old explicit errors hidden beyond the newest-200 supplemental scan.
- T10 remains NOT VERIFIED. Authoritative integration remains NOT COMPLETE. Terminal-Bench was not run.

VERIFIED:
- Current reviewed source was main commit 7021eddd0b6f41483de5ce078931f17a32e9fc05 before review publication.
- Local-vs-remote provenance distinction is explicit in provenance/LOCAL_CANONICAL_HISTORY.md.
- The four known remote import mismatches were corrected by commit fdb0fb58af7572b2c71ccc00baad2f0509f14e22; that correction changed comments only in fingerprint.py, retrieve.py, store.py, and test_v0_memory.py, so those intermediate byte mismatches do not change executable staging semantics.
- Snapshot 36/36 exactness is SUPPORTED_BUT_NOT_VERIFIED by Chat3 because a byte-for-byte current tree could not be independently materialized for recomputing all SHA-256 entries.
- No local-estimator substitution path was found in staging token_logger.py when provider usage is missing; it returns TOKEN_ACCOUNTING_INVALID.
- The message-bus next-ID helper has a real concurrent-allocation race because highest+1 is computed without reservation/CAS; current validation only detects duplicate IDs afterward.

EVIDENCE:
- reports/review/ADVERSARIAL_REVIEW_V0.md
- reviewed commit: 7021eddd0b6f41483de5ce078931f17a32e9fc05
- review-report commit: ea63772557e4d7d88cc50b6d226a47da51db990a
- implementation/staging/src/minisweagent/memory/retrieve.py
- implementation/staging/src/minisweagent/memory/fingerprint.py
- implementation/staging/src/minisweagent/memory/store.py
- implementation/staging/src/minisweagent/memory/context_builder.py
- implementation/staging/src/minisweagent/instrumentation/token_logger.py
- tests/staging/test_v0_memory.py
- scripts/message_bus.py
- tests/message_bus/test_message_bus.py
- provenance/SNAPSHOT_SHA256SUMS.txt
- provenance/LOCAL_CANONICAL_HISTORY.md
- new-test result: 12 total, 4 passed, 8 failed

OPEN_QUESTIONS:
- None requiring architecture redesign. Chat2 should implement only the minimal local fixes/regressions identified by the review before authoritative integration.

REQUESTED_ACTION:
- Route the review to CHAT2_IMPLEMENTER for the minimum fixes/regressions in reports/review/ADVERSARIAL_REVIEW_V0.md, then require Chat3 re-review before authoritative mini-SWE-agent integration proceeds.

DO_NOT_CHANGE:
- mini-SWE-agent v2.4.6
- upstream commit a83fcae82d2a08f0ee0c688f9d137b3566c097f8
- frozen v0 architecture
- GLM-5.3
- Terminal-Bench 3.0
- primary metric provider-reported total tokens / successful tasks
- benchmark task selection/configuration
