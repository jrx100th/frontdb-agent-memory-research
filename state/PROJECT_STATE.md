# Project State

## PROJECT
Agent Memory Efficiency Experiment

## STATUS
V0 architecture remains frozen.

The authoritative mini-SWE-agent v2.4.6 scientific baseline remains:

`81b7e326f91e5efdee43cf11349294c088e2731e`

The real GLM-5.3 / TokenRouter-compatible provider-accounting gate is **PASS**.

Chat3 independently reviewed the authoritative integration and returned:

**PROCEED_TO_BENCHMARK_REPRO_GATE**

Chat4 previously returned:

**BLOCKED_REPRO_IMPLEMENTATION_FIX_REQUIRED**

because executable B (Last-4-only, zero memory side effects) and D (pure lexical FTS/BM25 baseline sharing C storage/safety/budget) were missing.

Chat2 has now completed the authorized minimal condition-runner fix at:

`ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc`

Authoritative CI for that condition-runner object:

- run `33988970398`
- job `101367636620`
- conclusion: `success`
- deterministic condition-purity suite: `10 passed / 0 failed`
- Strong T10: **PASS**
- upstream: `606 passed / 0 failed / 13 skipped`

Baseline -> condition-runner changed exactly:

1. `.github/workflows/chat2-authoritative-integration.yml`
2. `implementation/authoritative/apply_condition_runner.py`
3. `tests/integration/test_condition_runner.py`

Frozen C repository sources/constants were not changed.

This Chat2 result is **IMPLEMENTATION-TESTED BUT NOT YET INDEPENDENTLY CLEARED BY CHAT4**.

Terminal-Bench execution remains **NOT RUN / NOT AUTHORIZED**.

## HARNESS
mini-SWE-agent v2.4.6

## UPSTREAM COMMIT
`a83fcae82d2a08f0ee0c688f9d137b3566c097f8`

## TESTED SCIENTIFIC BASELINE SHA
`81b7e326f91e5efdee43cf11349294c088e2731e`

## TESTED CONDITION-RUNNER SHA
`ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc`

Implementation branch:

`chat2/authoritative-integration-20260905`

The condition-runner SHA is the object Chat4 must independently review. It is not merged into coordination `main`.

## MODEL / PROVIDER
- model: GLM-5.3
- route: `z-ai/glm-5.3-free`
- provider transport: TokenRouter-compatible OpenAI format
- LiteLLM compatibility hint: `custom_llm_provider="openai"`
- LiteLLM version: `1.99.0`
- stream: `false`

## PRIMARY METRIC
provider-reported total tokens / successfully solved tasks

## AUTHORITATIVE PROVIDER ACCOUNTING
Final authoritative provider observation from the cleared baseline:

- input/prompt tokens: `186`
- output/completion tokens: `50`
- total tokens: `236`
- cached tokens: `0`
- reasoning tokens: `36`
- arithmetic consistency: `186 + 50 = 236`
- accounting status: `COUNTED`
- provider calls: attempted `1`, countable `1`, extra `0`
- local estimator substitution: none

## CHAT3 INDEPENDENT REVIEW
Published report:

`reports/review/AUTHORITATIVE_INTEGRATION_REVIEW_V0.md`

Verdict: **PROCEED_TO_BENCHMARK_REPRO_GATE**.

Independent reviewer CI:
- run `33983684722`
- job `101353282558`
- reviewer head `ee42f1cf36a6747410e13c16ddf386af34f98c52`
- Chat3 reviewer tests: `14 passed`
- provider accounting + adapter tests: `13 passed`
- Strong T10: **PASS**

## CONDITION-RUNNER IMPLEMENTATION STATUS
Chat2 publication handoff:

`messages/orchestrator/MSG-000028-chat2-to-orchestrator-condition-runner-review-handoff.md`

Chat2 requested Chat4 review in:

`messages/chat4_benchmark/MSG-000029-chat2-to-chat4-condition-harness-repro-review-request.md`

Implementation-tested semantics reported by Chat2:
- A = native full history, zero memory side effects
- B = system + original task + last 4 complete native steps verbatim; incomplete trailing step excluded; zero MemoryRuntime/DB/fingerprint/retrieval/synthetic-message work
- C = existing frozen structured-memory behavior unchanged
- D = same task-local storage/chunks/write policy/task isolation/freshness/staleness/fingerprint/budget/limits/framing/serialization as C, with pure lexical FTS/BM25 selection and no structured-ranking bonuses
- C_VS_D_ONLY_INTENDED_DIFFERENCE = PASS
- CONDITION_NEUTRAL_SETTINGS = PASS

These are not final scientific claims until Chat4 independently reproduces/clears them.

## CHAT4 REPRODUCIBILITY GATE
Terminal-Bench identity already verified without executing tasks:

- repository: `harbor-framework/terminal-bench`
- tag: `v3.0.0`
- immutable revision: `2b0442c3c583b710ca8da14c8e601b99f2f1f244`

The previous B/D blocker is now implementation-tested as repaired, but independent Chat4 verification is still required.

If Chat4 clears condition purity, Chat4 must then freeze and publish before any task execution:
- exact 10-15 task IDs and frozen order/schedule
- A/B/C/D execution semantics and isolation/reset rules
- provider/model/settings packet
- retry/caching/accounting-invalid policy
- measurement outputs
- final experiment manifest, fully populated, hashed, frozen, and read back

Final benchmark manifest: **NOT FROZEN**.

## ARTIFACT PROVENANCE RESERVATION
- artifact id: `9970944939`
- current API/downloaded-byte SHA-256: `339dc5ebf443df4f80d174b574d7a605c1b0a5e13cd767820cdd6af8792e0880`
- historical upload-log digest: `31b931226ee1bbddb1cd4dc67e395a32821f75323faa79a39e03fa854a596426`
- disposition: **UNRESOLVED_BUT_NONBLOCKING**

## PERFORMANCE RESERVATION
**HIGH PERFORMANCE RISK** remains active.

No retrieval optimization is authorized during the reproducibility gate.

## TERMINAL-BENCH
Benchmark family: Terminal-Bench 3.0

Pinned identity: `v3.0.0` at `2b0442c3c583b710ca8da14c8e601b99f2f1f244`.

Execution: **NOT RUN**.

Execution remains forbidden until Chat4 independently clears the condition-runner, freezes the exact task subset/schedule/settings and final experiment manifest, publishes/read-backs that packet, and explicitly returns `READY_TO_EXECUTE_BENCHMARK`.

## NEXT ACTION
**CHAT4 — INDEPENDENT CONDITION-HARNESS REPRODUCIBILITY REVIEW + MANIFEST FREEZE IF CLEAN**

No Terminal-Bench task execution during this gate.

## Evidence boundary
Engineering/provider/reviewer gates remain cleared. Chat2 has repaired the narrow B/D execution blocker under deterministic non-benchmark tests. The repair is not independently cleared yet. No claim that structured memory improves tokens per success has been tested.
