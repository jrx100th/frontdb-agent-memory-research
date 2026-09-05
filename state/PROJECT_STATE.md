# Project State

## PROJECT
Agent Memory Efficiency Experiment

## STATUS
V0 architecture remains frozen.

The authoritative mini-SWE-agent v2.4.6 integration remains tested at:

`81b7e326f91e5efdee43cf11349294c088e2731e`

The real GLM-5.3 / TokenRouter-compatible provider-accounting gate is **PASS**.

Chat3 independently reviewed the authoritative integration and returned:

**PROCEED_TO_BENCHMARK_REPRO_GATE**

Chat4 then performed the Benchmark/Reproducibility gate and correctly returned:

**BLOCKED_REPRO_IMPLEMENTATION_FIX_REQUIRED**

The blocker is narrow: the authoritative executable agent path exposes A (native full history) and C (structured memory), but does not yet expose executable B (Last-4-only with zero memory side effects) or D (pure lexical FTS/BM25 baseline with the same storage/safety/budget as C).

Terminal-Bench execution remains **NOT RUN / NOT AUTHORIZED**.

## HARNESS
mini-SWE-agent v2.4.6

## UPSTREAM COMMIT
`a83fcae82d2a08f0ee0c688f9d137b3566c097f8`

## TESTED SCIENTIFIC BASELINE SHA
`81b7e326f91e5efdee43cf11349294c088e2731e`

Only the minimal condition-runner implementation fix is now authorized. The frozen C algorithm/constants may not change.

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
Final authoritative provider observation:

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

## CHAT4 REPRODUCIBILITY GATE
Durable blocker handoff:

`messages/orchestrator/MSG-000026-chat4-to-orchestrator-repro-gate-blocked.md`

Chat4 verified Terminal-Bench identity without executing tasks:

- repository: `harbor-framework/terminal-bench`
- tag: `v3.0.0`
- immutable revision: `2b0442c3c583b710ca8da14c8e601b99f2f1f244`

Condition status:
- A: executable native full history with zero memory side effects
- B: **BLOCKED** — Last-4 helper exists but no authoritative Last-4-only executable mode with zero memory runtime/DB/fingerprint/retrieval work
- C: executable frozen structured-memory path
- D: **BLOCKED** — no pure lexical FTS/BM25 ranking-policy mode exists in the executable path

Because B/D are not executable, Chat4 did not freeze a task subset, condition schedule, prompt/provider packet, or final experiment manifest.

Final benchmark manifest: **NOT FROZEN**.

## AUTHORIZED MINIMAL IMPLEMENTATION FIX
Chat2 is authorized exactly once to expose a deterministic A/B/C/D condition selector and non-benchmark purity smoke tests.

Required semantics:
- A = native full history, zero memory side effects
- B = system + original task + last 4 complete native steps verbatim, zero MemoryRuntime/DB/fingerprinting/retrieval/synthetic-message work
- C = existing frozen structured-memory path unchanged
- D = same task-local memory storage/chunks/candidate eligibility/freshness/staleness/2048 budget/record limits/framing/serialization as C, but pure lexical FTS/BM25 ranking/selection instead of C's structured score

No other scientific implementation change is authorized.

After Chat2 completes and publishes the fix, control returns directly to Chat4 for independent condition-purity/reproducibility verification.

## ARTIFACT PROVENANCE RESERVATION
- artifact id: `9970944939`
- current API/downloaded-byte SHA-256: `339dc5ebf443df4f80d174b574d7a605c1b0a5e13cd767820cdd6af8792e0880`
- historical upload-log digest: `31b931226ee1bbddb1cd4dc67e395a32821f75323faa79a39e03fa854a596426`
- disposition: **UNRESOLVED_BUT_NONBLOCKING**

## PERFORMANCE RESERVATION
**HIGH PERFORMANCE RISK** remains active.

The condition-runner fix must not optimize or alter retrieval coefficients/constants.

## TERMINAL-BENCH
Benchmark family: Terminal-Bench 3.0

Pinned identity from Chat4 gate: `v3.0.0` at `2b0442c3c583b710ca8da14c8e601b99f2f1f244`.

Execution: **NOT RUN**.

Execution remains forbidden until Chat2's minimal B/D runner fix is independently cleared by Chat4, the exact frozen task subset/schedule/settings are published, and the final experiment manifest is frozen/read back.

## NEXT ACTION
**CHAT2 — MINIMAL REPRODUCIBILITY CONDITION-RUNNER FIX**

Then return immediately to Chat4.

## Evidence boundary
Engineering/provider/reviewer gates remain cleared. The current blocker is reproducibility infrastructure, not demonstrated failure of the structured-memory algorithm. No claim that structured memory improves tokens per success has been tested yet.
