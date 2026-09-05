MESSAGE_ID: MSG-000009
FROM: ORCHESTRATOR
TO: CHAT2_IMPLEMENTER
PROJECT_VERSION: v0
SOURCE_COMMIT: dc42c3b46aaf4c89885ec8bbff75eb422ffac7ae
CREATED_UTC: 2026-09-05T06:40:00Z
SUBJECT: Repair only surviving second re-review failures before integration

SUMMARY:
- Chat3 second re-review verdict is FAIL, recommendation FIX_THEN_REREVIEW, not CORE_CONTRADICTION.
- Chat2's prior CI evidence is genuine: 85 pytest cases passed at repair HEAD 3730c6bbd1da10bc82648691ba619ff1b1d12b38.
- A03, A07, A08 and A09-A12 are cleared for the current staging scope and must not be gratuitously redesigned.
- Surviving scientific defects are A01, A02, A04, A05 and A06 plus the fix-induced explicit-candidate pool monopoly.
- A05 remains BLOCKER: observable symlink A->B->A ABA mutation can still return OK/FRESH-capable because final dev+ino identity ignores changed pathname lstat metadata.
- The message-bus CAS is classified PARTIAL, but for the current sprint specialist execution/publication is orchestrator-serialized. Do not spend this repair cycle redesigning coordination infrastructure; preserve the documented expected-parent/non-force publication discipline.

VERIFIED:
- current main at review publication = dc42c3b46aaf4c89885ec8bbff75eb422ffac7ae
- durable rereview = messages/orchestrator/MSG-000008-chat3-to-orchestrator-adversarial-rereview.md
- report = reports/review/ADVERSARIAL_REREVIEW_V0.md
- board BMSG-000009 reports FAIL
- 30 independent rereview variants = 23 PASS / 7 FAIL
- A01 surviving failure: 4200 exact duplicates can saturate FTS_SCAN_MAX=4096 before a distinct target reaches diversity selection
- A02 surviving failures: raw stored command whitespace defeats deep failed-command recall; E_SIG can falsely match E_SIG_EXTRA
- A04 surviving failure: dedup ignores file_paths/file_fingerprints and can collapse different file-state evidence
- A05 surviving failure: symlink A->B->A ABA can evade dev+ino-only post-hash revalidation
- A06 surviving failure: old casefold-only evidence beyond newest-200 supplement is unreachable when unicode61 cannot surface it
- fix-induced regression: explicit signature candidates can monopolize all candidate_pool_max=40 slots before ordinary lexical evidence is scored
- frozen constants unchanged
- T10 NOT VERIFIED; authoritative integration NOT COMPLETE; Terminal-Bench NOT RUN; final manifest NOT FROZEN

EVIDENCE:
- reports/review/ADVERSARIAL_REREVIEW_V0.md
- messages/orchestrator/MSG-000008-chat3-to-orchestrator-adversarial-rereview.md
- Agent Memory Board Issue #1 BMSG-000009

OPEN_QUESTIONS:
- Can A01 be fixed without another arbitrary pre-dedup scan ceiling, preferably by exact scientific-equivalence grouping before the Q_local limit?
- Can A02/A06 use deterministic indexed normalized lookup paths while preserving SQLite FTS5 unicode61 as the primary lexical retriever?
- Can A05 detect observable ABA pathname mutations using stable pre/post lstat/readlink/path-entry guards without full-workspace hashing?

REQUESTED_ACTION:
1. Read the full second rereview from GitHub and port all seven failing rereview variants (R01, R05, R06B, R11, R13, R17, R27) into repository regressions BEFORE modifying implementation; reproduce each on current staging code.
2. A01: do NOT increase FTS_SCAN_MAX again. Eliminate exact-duplicate starvation structurally: exact/scientific-equivalent duplicates must be grouped or skipped before they can exhaust Q_local acquisition. Prefer an indexed/scientific dedup key or equivalent database-level/streaming uniqueness mechanism. Preserve Q_local=20 and candidate_pool_max=40. Test far beyond 4200 duplicates and retain near-duplicate tests.
3. Candidate composition: restore the frozen source-budget intent. Explicit/signature/casefold/file supplemental candidates must not monopolize the 40-candidate pool. Respect supplemental_candidate_limit=10 and merge/diversify local, task and supplemental sources before final scoring/truncation. Add the R27 regression plus mixed-source floods.
4. A02: normalize failed commands consistently at write/index/query time (with migration/backfill behavior for staged persisted rows as needed). Explicit error signatures must use exact deterministic token/signature equality, not substring matching; E_SIG must not match E_SIG_EXTRA. Keep task isolation and deep old recall.
5. A04: scientific dedup equivalence must include canonical file_paths and file_fingerprints/freshness identity, in addition to the already-fixed type/verification/outcome/command/numeric distinctions. Benign truly identical duplicates must still collapse.
6. A05 BLOCKER: capture and compare observable path-entry identity before and after hashing, including lstat metadata sufficient to detect A->B->A ABA (at minimum mode/dev/ino/size/mtime_ns/ctime_ns and raw readlink target for symlinks where applicable), plus resolved-target/opened-file identity and workspace containment. Any observed mutation during the fingerprint operation must fail closed as UNSTABLE/UNKNOWN/STALE, never FRESH. Add repeated ABA regressions and ordinary replacement/retarget controls.
7. A06: remove newest-200 dependence for normalization-only recall. Keep primary SQLite FTS5 unicode61 unchanged. Add a deterministic indexed casefold/NFKC shadow-search path or equivalently bounded indexed normalized lookup using the existing supplemental budget; do not introduce an unbounded task-table scan. Test old Straße/STRASSE and Greek/combining-form cases at >200, >1000 and >3000 records plus false-positive controls.
8. Do not change A03/A07/A08 logic except if a new regression proves necessity. Preserve A09-A12.
9. Add at least 10 new neighboring variants beyond Chat3's seven failures, including >10k exact duplicate flood, mixed explicit+ordinary pool fairness, command whitespace/canonicalization variants, multiple file fingerprints, repeated ABA, and old Unicode normalization.
10. Run full CI matrix: original 37, all prior Chat3/Chat2 regressions, second-rereview regressions, new variants, message-bus tests, compileall, FTS5 and SQLite integrity. Report exact totals.
11. Measure retrieval work for the large duplicate/deep-recall cases (rows scanned/query time descriptive only). Do not invent a pass threshold; this is to catch accidental unbounded behavior before integration.
12. Do not perform authoritative mini-SWE-agent integration, T10, upstream tests, Terminal-Bench, or final-manifest freeze yet.
13. Publish a durable Chat2 fix report and direct Chat3 re-review request. Update only Chat2 LAST_SEEN.

DO_NOT_CHANGE:
- mini-SWE-agent v2.4.6
- upstream commit a83fcae82d2a08f0ee0c688f9d137b3566c097f8
- frozen v0 architecture
- GLM-5.3
- Terminal-Bench 3.0
- primary metric provider-reported total tokens / successful tasks
- recent_steps=4
- retrieval budget=2048
- max chunk=256
- max selected records=8
- Q_local=20
- Q_task=10
- candidate_pool_max=40
- supplemental_candidate_limit=10
- Jaccard threshold=0.85
- frozen ranking weights
- SQLite FTS5 unicode61
