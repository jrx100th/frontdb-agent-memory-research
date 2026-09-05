MESSAGE_ID: MSG-000031
FROM: CHAT4_BENCHMARK
TO: ORCHESTRATOR
PROJECT_VERSION: v0-pre-integration-1
SOURCE_COMMIT: eec95f45132f9741234865d8a2f11eae3503ad81
CREATED_UTC: 2026-09-05T20:53:06Z
SUBJECT: Independent condition-harness review passed and final benchmark manifest frozen

SUMMARY:
Chat4 independently reviewed condition-runner ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc against cleared baseline 81b7e326f91e5efdee43cf11349294c088e2731e. The repair is restricted to the three authorized files; A/B purity passes; C is scientifically unchanged; D is a fair pure-lexical baseline on the shared C pipeline; condition neutrality and provider accounting remain intact. Terminal-Bench identity was reverified without executing agent tasks. Chat4 froze a self-contained final manifest with the 12-task subset/order, balanced A/B/C/D schedule, reset/isolation policy, provider packet, failure/accounting-invalid policy, metrics, and output schema. Verdict: READY_TO_EXECUTE_BENCHMARK.

VERIFIED:
- START_MAIN_HEAD = eec95f45132f9741234865d8a2f11eae3503ad81
- baseline = 81b7e326f91e5efdee43cf11349294c088e2731e
- condition runner = ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc
- diff = exactly three authorized files
- A = PASS; B = PASS; C unchanged = PASS; D lexical-only = PASS
- C/D shared pipeline = PASS
- condition neutrality = PASS
- accounting = PASS
- Strong T10 = PASS
- raw upstream JUnit independently recomputed: 606 passed / 13 skipped / 0 failures / 0 errors
- Terminal-Bench = harbor-framework/terminal-bench v3.0.0 at 2b0442c3c583b710ca8da14c8e601b99f2f1f244
- frozen task count = 12; all four conditions per task = 48 planned runs
- final manifest SHA-256 = fb5ace0c0f211cd37aad473845d7c2e818d0a5e518651919a0a5a67437c3449e
- Terminal-Bench agent tasks executed in this gate = NO
- artifact digest discrepancy retained
- HIGH PERFORMANCE RISK retained; latest exact-duplicate 10k stress approximately 20.129165 s

EVIDENCE:
- reports/benchmark/CONDITION_HARNESS_REPRO_REVIEW_V0.md
- manifests/experiment_manifest.final.json
- reproducibility/FINAL_MANIFEST_SHA256.txt
- Chat2 CI run/job 33988970398 / 101367636620
- evidence artifact 9976107970; downloaded ZIP SHA-256 07c8c5c9ac8f8657d0e12599ff722fb99f1c4b218d94ff45fe71deabcfd515e9

OPEN_QUESTIONS:
- None blocking execution under the frozen manifest. The structured-memory hypothesis remains UNTESTED.
- HIGH PERFORMANCE RISK remains an execution/runtime reservation.

REQUESTED_ACTION:
Authorize execution of the 48 frozen task-condition runs exactly under the final manifest. Do not alter task subset/order, condition schedule, prompts/tools/provider settings, retry/accounting rules, reset semantics, or metric definitions. Preserve raw evidence for independent aggregation.

DO_NOT_CHANGE:
- mini-SWE-agent v2.4.6
- upstream a83fcae82d2a08f0ee0c688f9d137b3566c097f8
- baseline 81b7e326f91e5efdee43cf11349294c088e2731e
- condition-runner ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc
- GLM-5.3 / z-ai/glm-5.3-free
- LiteLLM 1.99.0 / custom_llm_provider=openai / stream=false
- Terminal-Bench v3.0.0 revision 2b0442c3c583b710ca8da14c8e601b99f2f1f244
- frozen A/B/C/D semantics/constants
- frozen 12-task subset/order and cyclic schedule
- primary provider-reported tokens-per-success and invalid-accounting policy
- final manifest hash fb5ace0c0f211cd37aad473845d7c2e818d0a5e518651919a0a5a67437c3449e
