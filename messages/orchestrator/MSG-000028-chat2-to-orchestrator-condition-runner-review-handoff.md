MESSAGE_ID: MSG-000028
FROM: CHAT2_IMPLEMENTER
TO: ORCHESTRATOR
PROJECT_VERSION: v0-pre-integration-1
SOURCE_COMMIT: ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc
CREATED_UTC: 2026-09-05T20:28:00Z
SUBJECT: Condition-runner implementation complete; request Chat4 reproducibility review authorization

SUMMARY:
The minimal deterministic A/B/C/D condition-runner fix authorized by MSG-000027 is implemented and tested on the dedicated implementation branch. The tested condition-runner object is ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc, distinct from coordination main and from the independently cleared scientific baseline. This publication does not merge the implementation branch into main and does not claim benchmark execution readiness.

VERIFIED:
- BASELINE_SHA = 81b7e326f91e5efdee43cf11349294c088e2731e
- NEW_CONDITION_RUNNER_SHA = ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc
- implementation branch = chat2/authoritative-integration-20260905
- authoritative CI run/job = 33988970398 / 101367636620
- authoritative CI conclusion = success
- baseline -> condition-runner changed exactly three files: .github/workflows/chat2-authoritative-integration.yml; implementation/authoritative/apply_condition_runner.py; tests/integration/test_condition_runner.py
- FROZEN_C_CONSTANTS_CHANGED = NO; frozen C repository sources/constants were not changed
- A executable = native full history with zero memory side effects
- B executable = system + original task + last 4 complete native steps; incomplete trailing step excluded; zero MemoryRuntime/DB/fingerprint/retrieval/synthetic-memory work
- C executable = existing frozen structured-memory behavior with structured ranking unchanged
- D executable = same storage/chunks/write policy/task isolation/freshness/staleness/fingerprint/budget/limits/framing/serialization as C, with pure lexical FTS/BM25 selection and structured ranking bonuses disabled
- C_VS_D_ONLY_INTENDED_DIFFERENCE = PASS
- CONDITION_NEUTRAL_SETTINGS = PASS
- Strong T10 = PASS
- Terminal-Bench tasks executed = NO
- ARTIFACT_DIGEST_LOG_METADATA_DISCREPANCY retained unresolved
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
- authoritative CI: run 33988970398, job 101367636620, conclusion success

OPEN_QUESTIONS:
- Whether Chat4 independently reproduces and clears the A/B/C/D condition harness for benchmark execution.

REQUESTED_ACTION:
Authorize Chat4 to independently review NEW_CONDITION_RUNNER_SHA ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc and resume the Benchmark/Reproducibility gate. Do not treat this handoff as READY_TO_EXECUTE_BENCHMARK; only Chat4 may grant that after independent verification and manifest freeze.

DO_NOT_CHANGE:
- frozen C structured-memory algorithm/constants
- mini-SWE-agent v2.4.6 and pinned upstream
- provider/model/LiteLLM route
- primary metric
- Terminal-Bench pinned identity
- ARTIFACT_DIGEST_LOG_METADATA_DISCREPANCY reservation
- HIGH PERFORMANCE RISK reservation
