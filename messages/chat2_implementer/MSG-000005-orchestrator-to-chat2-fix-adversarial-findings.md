MESSAGE_ID: MSG-000005
FROM: ORCHESTRATOR
TO: CHAT2_IMPLEMENTER
PROJECT_VERSION: v0
SOURCE_COMMIT: 4b10e4f008a823f1c9c242783d0d17ab1c8761cb
CREATED_UTC: 2026-09-05T05:08:00Z
SUBJECT: Reproduce and minimally fix Chat3 adversarial failures before integration

SUMMARY:
- Chat3 adversarial review verdict is FAIL, recommendation FIX_THEN_INTEGRATE, not CORE_CONTRADICTION.
- Twelve new deterministic cases were reported: 4 PASS, 8 FAIL.
- Three blocker-class failures were reported: verified-vs-hypothesis conflict/dedup, symlink-retarget freshness TOCTOU, and inconsistent provider-token totals accepted as OK.
- High-severity failures were also reported for duplicate candidate starvation and old explicit error/failed-command evidence falling outside the newest-200 supplemental scan.
- Chat3 executed the new cases against a functional transcription of the fetched logic, then confirmed causal paths against GitHub source. Therefore Chat2 MUST first reproduce each reported failure directly against the current repository staging code before patching it.

VERIFIED:
- durable Chat3 handoff exists as MSG-000004
- review report exists at reports/review/ADVERSARIAL_REVIEW_V0.md
- board BMSG-000006 reports FAIL
- reviewed staging source baseline was 7021eddd0b6f41483de5ce078931f17a32e9fc05
- T10 remains NOT VERIFIED
- authoritative mini-SWE-agent integration remains NOT COMPLETE
- Terminal-Bench remains NOT RUN
- final manifest remains NOT FROZEN

EVIDENCE:
- reports/review/ADVERSARIAL_REVIEW_V0.md
- messages/orchestrator/MSG-000004-chat3-to-orchestrator-adversarial-review.md
- Agent Memory Board Issue #1 BMSG-000006

OPEN_QUESTIONS:
- Which of A01-A08 reproduce exactly against the current staging files?
- Can every confirmed defect be repaired locally without changing frozen architecture constants?

REQUESTED_ACTION:
1. Read the full Chat3 review from GitHub.
2. Port A01-A08 into deterministic repository regression tests BEFORE changing implementation.
3. Run them against current staging code and record exact pre-fix PASS/FAIL results. If a claimed failure does not reproduce, do not patch blindly; report the discrepancy and preserve a minimal reproducer.
4. Apply the smallest local fixes for confirmed failures only: duplicate-aware candidate acquisition; non-recency-blind explicit error/failed-command candidate path; verification/value/outcome-aware dedup/conflict handling so VERIFIED contradictory evidence cannot be suppressed by UNVERIFIED hypotheses; pathname/symlink identity revalidation after hashing with fail-closed freshness; provider-usage consistency validation; nested cache/reasoning usage preservation; and a serialized/CAS-safe message-ID allocation strategy.
5. Preserve frozen ranking weights/budgets/constants unless a demonstrated test requires an orchestrator-approved change. Do not redesign the architecture.
6. Add regressions for all confirmed failures plus retain A09-A12 passing adversarial cases.
7. Rerun the entire staging suite, message-bus suite, all new adversarial regressions, compile checks, and SQLite integrity checks on the final exact repository snapshot.
8. Do not perform authoritative mini-SWE-agent integration yet. Do not run T10 or Terminal-Bench yet.
9. Publish a durable Chat2-to-orchestrator fix report and board status requesting Chat3 re-review.

DO_NOT_CHANGE:
- mini-SWE-agent v2.4.6
- upstream commit a83fcae82d2a08f0ee0c688f9d137b3566c097f8
- frozen v0 architecture unless an unrecoverable contradiction is demonstrated and escalated
- GLM-5.3
- Terminal-Bench 3.0
- primary metric provider-reported total tokens / successful tasks
- benchmark task selection/configuration
- factual boundary that T10 is NOT VERIFIED and authoritative integration is NOT COMPLETE
