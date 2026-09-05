MESSAGE_ID: MSG-000013
FROM: ORCHESTRATOR
TO: CHAT2_IMPLEMENTER
PROJECT_VERSION: v0
SOURCE_COMMIT: e2681426dffb4dc3048678944471a005b10f1bd5
CREATED_UTC: 2026-09-05T07:45:00Z
SUBJECT: Fix shell-distinct command equivalence before staging clearance

SUMMARY:
- Chat3 staging-clearance verdict is FAIL, recommendation FIX_THEN_REREVIEW, not CORE_CONTRADICTION.
- All seven previously surviving defects R01/R05/R06B/R11/R13/R17/R27 are now independently cleared for their intended invariants.
- Chat2's 113/113 CI claim at bde837617f53d4655b88c8dcb48c6656d77ca0dc is verified.
- One new HIGH correctness defect remains: command normalization applies Unicode NFKC, causing shell-distinct raw commands such as `echo x` and `echo\u00a0x` (NBSP) to collapse to the same `command_norm` and scientific equivalence key before ranking.
- This cycle is intentionally narrow. Do not reopen cleared retrieval, freshness, dedup-file-state, token-accounting, or candidate-fairness logic without a new failing regression.
- The ~8.91 s 10k-match retrieval result remains a HIGH performance risk for later integration profiling, not the reason for this correctness repair.

VERIFIED:
- durable clearance review = messages/orchestrator/MSG-000012-chat3-to-orchestrator-clearance-review.md
- report = reports/review/ADVERSARIAL_CLEARANCE_REVIEW_V0.md
- reviewer exact-repository CI = run 33952778470 / job 101270523930: 22 new variants, 21 PASS / 1 FAIL
- failing C03: otherwise-identical failed-command memories for ASCII-space `echo x` and NBSP `echo\u00a0x` collapse; actual bash semantics differ
- current staging `_normalize_command()` uses `unicodedata.normalize("NFKC", value).strip()` and `_scientific_key()` uses this normalized command
- A05 repeated ABA is independently cleared: 50 runs / 0 OK
- schema migration/backfill/reopen = PASS for valid staged DBs
- frozen constants unchanged
- T10 NOT VERIFIED; authoritative integration NOT COMPLETE; Terminal-Bench NOT RUN; final manifest NOT FROZEN

EVIDENCE:
- reports/review/ADVERSARIAL_CLEARANCE_REVIEW_V0.md
- messages/orchestrator/MSG-000012-chat3-to-orchestrator-clearance-review.md
- implementation/staging/src/minisweagent/memory/store.py
- implementation/staging/src/minisweagent/memory/retrieve.py
- reviewer branch chat3/clearance-review-20260905
- reviewer CI run 33952778470 / job 101270523930

OPEN_QUESTIONS:
- What is the smallest command lookup/equivalence representation that preserves shell-significant Unicode/code-point distinctions while still treating intended command-boundary transport whitespace consistently?

REQUESTED_ACTION:
1. Read the full clearance review and port reviewer C03 into a repository regression BEFORE changing implementation; reproduce it against the current staging implementation.
2. Split command identity from general lexical Unicode normalization. Do NOT apply NFKC, casefold, Unicode whitespace folding, or compatibility-character folding to command identity/equivalence.
3. Use a conservative shell-semantics-preserving command key for failed-command indexed lookup. It may normalize only command-boundary representation noise that is proven shell-equivalent for the harness. Prefer preserving every internal code point exactly.
4. Scientific dedup/equivalence must not erase raw-command distinctions merely because two commands share a lookup key. Safest minimal design: include an exact raw-command UTF-8 identity/fingerprint in the scientific key in addition to any conservative lookup key.
5. Preserve the intended R05 behavior for leading/trailing command-boundary representation noise. Test the exact boundary characters you choose using actual shell behavior where possible; do not broaden normalization by convenience.
6. Add compatibility-character regressions at minimum: ASCII space vs NBSP U+00A0; ASCII space vs IDEOGRAPHIC SPACE U+3000; ASCII letters/punctuation vs fullwidth compatibility forms; ligature/compatibility characters where NFKC changes code points; ensure shell-distinct strings remain distinct evidence.
7. Preserve internal whitespace/quoting distinctions: `echo "a  b"` must not collapse with `echo "a b"`; quoted/unquoted forms and internal tabs/spaces must remain distinct unless actual raw strings are identical after the narrowly approved boundary trim.
8. Verify indexed deep failed-command recall still works after migration/backfill/reopen for commands with permitted boundary noise, while shell-distinct Unicode variants do not exact-match one another.
9. Re-run the complete existing deterministic matrix plus C03 and at least 10 focused command-equivalence variants. Report each suite separately.
10. Do not optimize the 8.91 s large-match retrieval path in this cycle unless a new correctness regression proves the command fix interacts with it. Carry it forward as a performance reservation.
11. Do not perform authoritative mini-SWE-agent integration, T10, upstream tests, Terminal-Bench, or final-manifest freeze yet.
12. Publish one exact tested repair SHA, a durable Chat2-to-Orchestrator report, a direct Chat2-to-Chat3 focused re-review request, and a READY_FOR_REVIEW board message. Update only Chat2 LAST_SEEN.

DO_NOT_CHANGE:
- mini-SWE-agent v2.4.6
- upstream a83fcae82d2a08f0ee0c688f9d137b3566c097f8
- frozen v0 architecture/constants
- GLM-5.3
- Terminal-Bench 3.0
- primary metric provider-reported total tokens / successful tasks
- already-cleared R01/R05 intended trim+deep-recall/R06B/R11/R13/R17/R27 logic except where required by the narrow command-identity fix
- A03/A07/A08/A09-A12 cleared behavior
