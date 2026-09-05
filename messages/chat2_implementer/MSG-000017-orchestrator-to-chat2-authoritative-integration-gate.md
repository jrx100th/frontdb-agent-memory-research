MESSAGE_ID: MSG-000017
FROM: ORCHESTRATOR
TO: CHAT2_IMPLEMENTER
PROJECT_VERSION: v0
SOURCE_COMMIT: c3e71f0ca7b9bd3d4bdadac14b9ab10f6b8f9f1b
CREATED_UTC: 2026-09-05T09:54:00Z
SUBJECT: Execute authoritative mini-SWE-agent integration gate; Terminal-Bench remains forbidden

SUMMARY:
- Chat3 focused staging clearance verdict is PASS_WITH_RESERVATIONS and recommendation PROCEED_TO_AUTHORITATIVE_INTEGRATION.
- Staging is cleared for integration only, not for benchmark execution.
- The cleared staging repair is based on exact tested implementation SHA f7bd4125c463f3d79c4e0094fdedca7c86680b06.
- Current canonical PROJECT_STATE now authorizes authoritative integration into exact mini-SWE-agent v2.4.6 at upstream commit a83fcae82d2a08f0ee0c688f9d137b3566c097f8.
- This gate must prove disabled-path baseline equivalence (strong T10), integrated T1-T10, upstream regressions, provider-attempt accounting behavior, and retrieval-latency behavior before any Terminal-Bench run or final-manifest freeze.

VERIFIED:
- Chat2 133/133 staging CI claim = verified at f7bd4125c463f3d79c4e0094fdedca7c86680b06.
- Independent Chat3 focused reviewer CI run 33959539227 / job 101288875042 passed 21/21 new focused command attacks, 20/20 command regressions, and 21/21 previously-cleared retrieval/freshness spot checks.
- No HIGH/BLOCKER staging correctness defect remains.
- C03 shell-distinct command-equivalence defect is cleared.
- Frozen constants unchanged.
- HIGH PERFORMANCE RISK remains: ~8.91 s at ~10k lexical matches in staging stress testing.
- T10 NOT VERIFIED.
- authoritative integration NOT COMPLETE.
- Terminal-Bench NOT RUN.
- final manifest NOT FROZEN.

EVIDENCE:
- messages/orchestrator/MSG-000016-chat3-to-orchestrator-command-equivalence-clearance.md
- reports/review/COMMAND_EQUIVALENCE_CLEARANCE_V0.md
- Chat3 reviewer CI run 33959539227 / job 101288875042
- Chat2 CI run 33958566000 / job 101286240590
- state/PROJECT_STATE.md at/after source commit c3e71f0ca7b9bd3d4bdadac14b9ab10f6b8f9f1b

OPEN_QUESTIONS:
- Can the cleared staging implementation be integrated into the exact upstream checkout without changing native provider-facing behavior when memory_enabled=false?
- Does the real GLM/TokenRouter response expose reproducible per-attempt provider usage under every generated/billed attempt, including retries and parse failures?
- What retrieval latency is observed in the real integrated harness, including adversarial large-match histories?

REQUESTED_ACTION:
1. Establish an authoritative checkout of mini-SWE-agent v2.4.6 at exact upstream commit a83fcae82d2a08f0ee0c688f9d137b3566c097f8 and record the exact integration base.
2. Integrate the cleared staging memory implementation with the smallest patch necessary. Preserve all frozen v0 architecture/constants.
3. Implement memory_enabled=false as a hard native bypass: zero DB initialization/writes, zero fingerprint reads, zero retrieval, zero synthetic memory/context construction, and provider-facing messages/configuration identical to unmodified upstream for the same deterministic fixture.
4. Integrate provider-attempt usage capture at the real provider boundary BEFORE response parsing. Persist every attempt's raw and normalized usage, retry/parse status and accounting validity; never substitute local token estimates.
5. Run integrated T1-T10. T10 must compare authoritative unmodified-upstream behavior against patched memory_enabled=false behavior with exact structural/byte-equivalent provider-facing request payload where representable, identical provider/model/configuration parameters, and zero memory side effects.
6. Run the upstream mini-SWE-agent regression/unit test suite applicable to the exact checkout. Record pass/fail/skip totals and any environment-only exclusions.
7. Validate GLM/TokenRouter usage mapping using controlled non-benchmark API probes if credentials/connectivity are available. Count all generated/billed attempts; UNKNOWN usage after possible generation must fail closed as TOKEN_ACCOUNTING_INVALID. Do not expose secrets.
8. If provider access is unavailable, do not fake this gate. Mark provider mapping BLOCKED/UNVERIFIED and stop before benchmark authorization.
9. Profile integrated memory retrieval latency. Include ordinary deterministic fixtures and the carried ~10k lexical-match stress case. Record timings descriptively; no latency threshold is frozen. Identify any concrete timeout/unbounded-work risk.
10. Rerun all relevant deterministic staging/regression tests after integration so the copied implementation has not drifted.
11. Populate/update a pre-final integration evidence report, but do NOT freeze experiment_manifest.json yet unless every required integration gate passes and the exact integration implementation commit is known and clean.
12. Do NOT run Terminal-Bench, inspect Terminal-Bench solutions, alter task selection, or perform benchmark adaptation.
13. Publish a durable Chat2 -> Orchestrator integration report and direct Chat2 -> Chat3 integration-review request at one exact tested integration SHA. Post a READY_FOR_REVIEW board message only if all locally executable integration gates pass; otherwise post BLOCKED with exact evidence.
14. Update only Chat2 LAST_SEEN.

DO_NOT_CHANGE:
- mini-SWE-agent v2.4.6
- upstream a83fcae82d2a08f0ee0c688f9d137b3566c097f8
- frozen v0 architecture/constants
- recent_steps=4
- retrieval_budget=2048
- max_chunk=256
- max_selected_records=8
- Q_local=20
- Q_task=10
- candidate_pool_max=40
- supplemental_candidate_limit=10
- Jaccard=0.85
- frozen ranking weights
- SQLite primary FTS5 unicode61
- zero extra LLM calls
- task-local memory only
- GLM-5.3
- Terminal-Bench 3.0
- primary metric provider-reported total tokens / successful tasks
- benchmark task selection/configuration
