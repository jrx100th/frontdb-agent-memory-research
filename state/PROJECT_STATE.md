# Project State

## PROJECT
Agent Memory Efficiency Experiment

## STATUS
**BENCHMARK EXECUTION AUTHORIZED — FROZEN 48-RUN EXPERIMENT**

The v0 architecture remains frozen. Engineering, provider-accounting, adversarial-review, and benchmark/reproducibility gates are cleared. Chat4 independently cleared the A/B/C/D condition harness, froze the benchmark packet, and completed the two final pre-execution identity requirements before any benchmark agent run or benchmark provider call occurred.

The Orchestrator authorizes execution via:

`messages/chat4_benchmark/MSG-000033-orchestrator-to-chat4-execute-frozen-benchmark.md`

No benchmark result has yet established the structured-memory hypothesis.

## FINAL FROZEN EXPERIMENT MANIFEST
Path:

`manifests/experiment_manifest.final.json`

Current authoritative SHA-256:

`88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a`

This supersedes pre-execution manifest hash:

`fb5ace0c0f211cd37aad473845d7c2e818d0a5e518651919a0a5a67437c3449e`

Reason:

`PRE_EXECUTION_REPRODUCIBILITY_IDENTITY_COMPLETION`

`final_frozen=true`.

## HARNESS / IMPLEMENTATION
- mini-SWE-agent: `v2.4.6`
- upstream commit: `a83fcae82d2a08f0ee0c688f9d137b3566c097f8`
- tested scientific baseline: `81b7e326f91e5efdee43cf11349294c088e2731e`
- tested condition-runner: `ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc`
- frozen C structured-memory algorithm/constants changed by condition-runner fix: **NO**
- Strong T10: **PASS**

## CONDITIONS
- **A — FULL NATIVE HISTORY:** pristine/native full history; zero memory runtime/DB/fingerprint/retrieval/synthetic-memory side effects.
- **B — LAST-4:** system + original task + last 4 complete native steps verbatim; zero memory side effects.
- **C — STRUCTURED MEMORY:** frozen structured-memory path + Last-4.
- **D — LEXICAL ONLY:** same storage/chunks/safety/freshness/budget/framing/serialization as C; pure FTS5/BM25-derived lexical ranking only.

A/B/C/D differ only by the frozen history/memory treatment.

## MODEL / PROVIDER
- model: GLM-5.3
- route: `z-ai/glm-5.3-free`
- provider transport: TokenRouter-compatible OpenAI chat-completions
- LiteLLM: `1.99.0`
- `custom_llm_provider="openai"`
- `stream=false`

Expected exact runtime provider-base SHA-256:

`f76d53a0e94e3837023542b48c5b2226b21c3ad37cae446272a2743b7579ee5d`

Before every provider invocation, hash the exact runtime `TOKENROUTER_BASE_URL` UTF-8 value without trimming/normalization. Mismatch => `CONFIGURATION_INVALID` and `ABORT_BEFORE_PROVIDER_CALL`.

API keys remain external secrets and must never be committed, printed, or hashed into public evidence.

## AUTHORITATIVE PROVIDER ACCOUNTING
Cleared provider observation:
- input/prompt tokens: `186`
- output/completion tokens: `50`
- total tokens: `236`
- cached tokens: `0`
- reasoning tokens: `36`
- arithmetic: `186 + 50 = 236`
- accounting status: `COUNTED`
- no local-estimator substitution

Primary scientific accounting uses provider-reported usage only. Retries/generated attempts count. Cached tokens are not subtracted. Reasoning tokens are not added again. Missing/malformed/unrecoverable usage => `UNKNOWN` / `TOKEN_ACCOUNTING_INVALID` under the frozen paired invalidation policy.

## TERMINAL-BENCH
- repository: `harbor-framework/terminal-bench`
- tag: `v3.0.0`
- immutable revision: `2b0442c3c583b710ca8da14c8e601b99f2f1f244`
- frozen task count: `12`
- planned task-condition runs: `48`

Frozen task order:
1. `atrx-vep-crispr`
2. `batched-eval-parity`
3. `cad-model`
4. `cargo-flight-dispatch`
5. `coq-block-bound`
6. `cumulative-layout-shift`
7. `data-anonymization`
8. `live-database-cutover`
9. `music-harmony`
10. `uefi-bootkit`
11. `production-planning`
12. `wdm-design`

Frozen cyclic condition schedule:
- task 1: `ABCD`
- task 2: `BCDA`
- task 3: `CDAB`
- task 4: `DABC`
- repeat this four-task cycle three times over the 12 frozen tasks.

No retrospective task replacement and no adaptive reordering.

## TASK ENVIRONMENT IDENTITY FREEZE
Packet:

`reproducibility/TASK_ENVIRONMENT_IDENTITIES.json`

Packet SHA-256:

`26566fea65da18291160d2f45598942182d4edf23e1b95485734bc196a67945e`

The packet binds, for all 12 tasks, pinned task metadata, complete environment Git-tree identity, container-definition identities, and resolved immutable external base-image digests. Before every provider call, verify the frozen environment identity. Any mismatch => `CONFIGURATION_INVALID` or `INFRASTRUCTURE_INVALID` and `ABORT_BEFORE_PROVIDER_CALL`.

Runtime-built task image digest remains mandatory and must match across A/B/C/D for that task before provider invocation.

## PRIMARY METRIC
`tokens_per_success = total_provider_tokens_across_condition / successfully_solved_tasks`

Thresholds remain frozen:
- >=30% lower with equal/higher solve rate: strong
- >=20% lower with no meaningful solve-rate loss: worthwhile
- <10%, meaningful solve-rate loss, or Last-4 closely matching C: stop/simplify signal

## PREVIOUS INDEPENDENT GATES
Chat3 authoritative-integration verdict:

**PROCEED_TO_BENCHMARK_REPRO_GATE**

Chat4 final reproducibility verdict:

**READY_TO_EXECUTE_BENCHMARK**

Latest Chat4 pre-execution identity handoff:

`messages/orchestrator/MSG-000032-chat4-to-orchestrator-prebenchmark-identity-freeze-complete.md`

Latest Orchestrator benchmark authorization:

`messages/chat4_benchmark/MSG-000033-orchestrator-to-chat4-execute-frozen-benchmark.md`

## RESERVATIONS
### Artifact provenance
`ARTIFACT_DIGEST_LOG_METADATA_DISCREPANCY` remains **UNRESOLVED_BUT_NONBLOCKING**.

### Performance
**HIGH PERFORMANCE RISK** remains retained. Duplicate-heavy retrieval showed materially worse latency than ordinary profiles. Retrieval-induced runtime/timeout is a real condition outcome and must not be selectively excluded.

## BENCHMARK EXECUTION RULE
Execute exactly the frozen 48 scheduled task-condition runs under manifest SHA-256:

`88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a`

Preserve raw trajectory, raw provider attempt usage, evaluator output, runtime logs, and C/D retrieval telemetry for every run. Do not alter tasks, schedule, prompts/tools, provider settings, condition semantics, memory constants, retry/accounting policy, invalidation policy, reset/isolation policy, or metrics after any benchmark result is observed.

If a frozen preflight or accounting/infrastructure rule fails, fail closed and preserve the failure. Do not silently repair or rerun outside the frozen policy.

## NEXT ACTION
**CHAT4 — EXECUTE THE 48 FROZEN BENCHMARK RUNS AND PUBLISH RAW EVIDENCE + CONDITION-NEUTRAL AGGREGATION.**

The structured-memory hypothesis remains **UNTESTED** until the frozen runs are completed and analyzed.

## PROVENANCE NOTE
Chat4 accidentally created `noop.txt` in commit `46eaf6607f17b3ebd15c23061b0aa09103b98843` and immediately removed it in `a075290ca1c46496c53c4e05aa642c4b719d43b1`. The incident touched only `noop.txt`; no scientific file changed. The repository tree returned to the prior pre-incident tree before the real pre-execution identity-freeze publication.
