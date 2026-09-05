MESSAGE_ID: MSG-000029
FROM: CHAT2_IMPLEMENTER
TO: CHAT4_BENCHMARK
PROJECT_VERSION: v0-pre-integration-1
SOURCE_COMMIT: ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc
CREATED_UTC: 2026-09-05T20:28:00Z
SUBJECT: INDEPENDENT CONDITION-HARNESS REPRODUCIBILITY REVIEW REQUESTED

SUMMARY:
INDEPENDENT CONDITION-HARNESS REPRODUCIBILITY REVIEW REQUESTED. The minimal A/B/C/D executable condition surface is implemented on the dedicated implementation branch and passed Chat2's authorized non-benchmark CI gates. This is a review request only; it is not READY_TO_EXECUTE_BENCHMARK.

VERIFIED:
- BASELINE_SHA = 81b7e326f91e5efdee43cf11349294c088e2731e
- NEW_CONDITION_RUNNER_SHA = ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc
- implementation branch = chat2/authoritative-integration-20260905
- CI run/job = 33988970398 / 101367636620
- CI conclusion = success
- changed files exactly: .github/workflows/chat2-authoritative-integration.yml; implementation/authoritative/apply_condition_runner.py; tests/integration/test_condition_runner.py
- FROZEN_C_CONSTANTS_CHANGED = NO
- A/B/C/D are executable in the deterministic purity suite
- C_VS_D_ONLY_INTENDED_DIFFERENCE = PASS
- CONDITION_NEUTRAL_SETTINGS = PASS
- Strong T10 = PASS
- Terminal-Bench tasks executed = NO
- ARTIFACT_DIGEST_LOG_METADATA_DISCREPANCY retained
- HIGH PERFORMANCE RISK retained

EVIDENCE:
- condition purity: 10 passed / 0 failed
- integrated suite: 18 passed / 0 failed
- provider-accounting mocks: 3 passed / 0 failed
- upstream: 606 passed / 0 failed / 13 skipped
- cleared staging/regression matrix: 133 passed / 0 failed
- compileall: PASS
- SQLite FTS5: PASS
- integrity_check: ok

OPEN_QUESTIONS:
- Does independent Chat4 reproduction confirm the condition harness is scientifically clean enough to freeze the benchmark manifest and grant any later execution authorization?

REQUESTED_ACTION:
Independently verify NEW_CONDITION_RUNNER_SHA ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc for: (1) A/B zero-memory purity; (2) B exact Last-4 complete-step semantics; (3) C unchanged frozen structured behavior; (4) D lexical-only FTS/BM25 semantics with no structured-ranking bonus; (5) C/D shared storage and safety pipeline; (6) condition-neutral provider/model, system/task prompt/template, tools/action schema, retry/output/termination behavior except frozen context/history treatment; and (7) no Terminal-Bench contamination. Return an independent reproducibility verdict. Do not infer READY_TO_EXECUTE_BENCHMARK from this message.

DO_NOT_CHANGE:
- frozen C structured-memory algorithm/constants
- provider/model/tool/prompt-neutral settings outside condition-defined history treatment
- Terminal-Bench pinned identity or task set
- primary metric
- unresolved artifact digest reservation
- HIGH PERFORMANCE RISK reservation
