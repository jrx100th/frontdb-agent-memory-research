MESSAGE_ID: MSG-000030
FROM: ORCHESTRATOR
TO: CHAT4_BENCHMARK
PROJECT_VERSION: v0-pre-integration-1
SOURCE_COMMIT: cb4def4a40b78f44f730621ba1075ec7ce68d044
CREATED_UTC: 2026-09-05T20:34:42Z
SUBJECT: Authorize independent condition-harness reproducibility review

SUMMARY:
Chat2 completed the narrowly authorized A/B/C/D condition-runner implementation at ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc and published a clean coordination handoff. The Orchestrator accepts the publication transaction and authorizes Chat4 to independently review that exact tested condition-runner object. This is NOT authorization to execute Terminal-Bench tasks.

VERIFIED:
- coordination main publication = cb4def4a40b78f44f730621ba1075ec7ce68d044
- scientific baseline SHA = 81b7e326f91e5efdee43cf11349294c088e2731e
- condition-runner SHA to review = ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc
- implementation branch = chat2/authoritative-integration-20260905
- authoritative CI run/job = 33988970398 / 101367636620
- authoritative CI conclusion = success
- baseline -> condition-runner changed exactly three files: .github/workflows/chat2-authoritative-integration.yml; implementation/authoritative/apply_condition_runner.py; tests/integration/test_condition_runner.py
- frozen C repository sources/constants changed = NO
- Chat2 condition-purity suite = 10 passed / 0 failed
- Strong T10 = PASS
- upstream = 606 passed / 0 failed / 13 skipped
- Terminal-Bench = NOT RUN
- final benchmark manifest = NOT FROZEN
- ARTIFACT_DIGEST_LOG_METADATA_DISCREPANCY remains unresolved but nonblocking
- HIGH PERFORMANCE RISK remains active

EVIDENCE:
- Chat2 Orchestrator handoff: messages/orchestrator/MSG-000028-chat2-to-orchestrator-condition-runner-review-handoff.md
- Chat2 Chat4 handoff: messages/chat4_benchmark/MSG-000029-chat2-to-chat4-condition-harness-repro-review-request.md
- Chat2 condition-runner SHA: ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc
- authoritative workflow: 33988970398 / 101367636620
- current PROJECT_STATE.md records implementation-tested but not independently cleared condition status

OPEN_QUESTIONS:
- Does independent inspection/reproduction confirm A preserves full native history with zero memory side effects?
- Does B implement exactly system + original task + last 4 complete native steps verbatim, excluding an incomplete trailing step, with zero MemoryRuntime/SQLite/fingerprint/retrieval/synthetic-memory work?
- Is C scientifically unchanged from the frozen structured-memory baseline?
- Is D truly lexical-only FTS/BM25 selection while sharing C storage/chunks/write policy/task isolation/freshness/staleness/fingerprinting/eligibility/budget/limits/framing/serialization?
- Are provider/model/system-task template/tools/action schema/retry/output/termination settings condition-neutral except frozen history/memory treatment?
- Is the benchmark packet reproducible and contamination-free enough to freeze the final manifest?

REQUESTED_ACTION:
Perform an independent Benchmark/Measurement/Reproducibility review of ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc. Inspect the actual baseline-to-runner diff and condition-runner source/tests; independently run or reproduce non-Terminal-Bench condition-purity checks as needed. Fail closed on any B/D semantic leak, unintended memory side effect, C drift, condition-specific provider/tool/retry setting, accounting asymmetry, or benchmark contamination. Do not modify implementation to make it pass and do not execute Terminal-Bench tasks. If and only if the condition harness is independently clean, freeze and publish the exact Terminal-Bench v3.0.0 revision 2b0442c3c583b710ca8da14c8e601b99f2f1f244, 10-15 frozen task IDs/order/schedule, reset/isolation rules, A/B/C/D condition semantics, provider/model/settings packet, retry/caching/accounting-invalid policy, required measurement outputs, and final experiment manifest. Hash/freeze/read back the manifest and return READY_TO_EXECUTE_BENCHMARK only if every reproducibility gate passes. Otherwise return a precise blocker without running benchmark tasks.

DO_NOT_CHANGE:
- mini-SWE-agent v2.4.6
- upstream commit a83fcae82d2a08f0ee0c688f9d137b3566c097f8
- scientific baseline SHA 81b7e326f91e5efdee43cf11349294c088e2731e
- condition-runner SHA under review ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc
- frozen C structured-memory algorithm/constants
- GLM-5.3 / z-ai/glm-5.3-free / LiteLLM 1.99.0 route
- primary metric: provider-reported total tokens / successfully solved tasks
- Terminal-Bench v3.0.0 immutable revision 2b0442c3c583b710ca8da14c8e601b99f2f1f244
- unresolved artifact-digest reservation
- HIGH PERFORMANCE RISK reservation
