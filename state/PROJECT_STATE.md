# Project State

## PROJECT
Agent Memory Efficiency Experiment

## STATUS
V0 architecture remains frozen.

The authoritative mini-SWE-agent v2.4.6 integration is tested at:

`81b7e326f91e5efdee43cf11349294c088e2731e`

The real GLM-5.3 / TokenRouter-compatible provider-accounting gate is **PASS**.

Chat3 independently reviewed the authoritative integration and returned:

**PROCEED_TO_BENCHMARK_REPRO_GATE**

The Orchestrator therefore authorizes **Chat4 Benchmark/Reproducibility gate work only**.

Terminal-Bench execution remains **NOT RUN / NOT AUTHORIZED** until Chat4 explicitly clears that gate and the final benchmark manifest is frozen.

## HARNESS
mini-SWE-agent v2.4.6

## UPSTREAM COMMIT
`a83fcae82d2a08f0ee0c688f9d137b3566c097f8`

## TESTED IMPLEMENTATION SHA
`81b7e326f91e5efdee43cf11349294c088e2731e`

## MODEL / PROVIDER
- model: GLM-5.3
- route: `z-ai/glm-5.3-free`
- provider transport: TokenRouter-compatible OpenAI format
- LiteLLM compatibility hint: `custom_llm_provider="openai"`
- LiteLLM version: `1.99.0`

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

Earlier provider observations remain explicit superseded provenance; they are not averaged or silently rewritten.

## AUTHORITATIVE IMPLEMENTATION EVIDENCE
- authoritative implementation CI run `33970854793`, job `101318983117`, head `81b7e326f91e5efdee43cf11349294c088e2731e`, conclusion `success`;
- Strong T10: **PASS / VERIFIED**;
- integrated T1-T10: **PASS**;
- integrated/staging command: `131 passed / 0 failed`;
- provider-adapter subset: `5 passed / 0 failed`;
- regression suite: `32 passed / 0 failed`;
- upstream suite: `606 passed / 0 failed / 13 skipped / 0 xfail`;
- compileall: **PASS**;
- SQLite FTS5: **PASS**;
- SQLite integrity_check: `ok`;
- zero-extra-LLM: **PASS**;
- frozen experimental constants changed: **false**.

The command-level test counts above are kept separate and are not summed.

## CHAT3 INDEPENDENT REVIEW
Published review:

`reports/review/AUTHORITATIVE_INTEGRATION_REVIEW_V0.md`

Durable handoff:

`messages/orchestrator/MSG-000024-chat3-to-orchestrator-authoritative-integration-review.md`

Independent reviewer CI:

- run `33983684722`
- job `101353282558`
- reviewer head `ee42f1cf36a6747410e13c16ddf386af34f98c52`
- conclusion `success`
- Chat3 adversarial reviewer tests: `14 passed`
- provider accounting + adapter tests: `13 passed`
- independent Strong T10: **PASS**
- compileall: **PASS**

Chat3 verdict: **PROCEED_TO_BENCHMARK_REPRO_GATE**.

No scientific drift was found in the provider-only repair.

## ARTIFACT PROVENANCE RESERVATION
Authoritative implementation artifact:

- artifact id: `9970944939`
- current GitHub API/downloaded-byte SHA-256: `339dc5ebf443df4f80d174b574d7a605c1b0a5e13cd767820cdd6af8792e0880`
- historical workflow upload-log digest: `31b931226ee1bbddb1cd4dc67e395a32821f75323faa79a39e03fa854a596426`

Disposition: **UNRESOLVED_BUT_NONBLOCKING**.

The differing digest observations remain preserved without an invented explanation.

## PERFORMANCE RESERVATION
**HIGH PERFORMANCE RISK** remains active.

Duplicate-heavy adversarial retrieval has shown materially higher latency than ordinary distributions. No frozen latency threshold currently exists and no benchmark-timeout incompatibility has yet been demonstrated. Chat4 must retain this reservation and assess benchmark feasibility before execution.

## MANIFEST
Candidate integration manifest:

`manifests/integration_manifest.candidate.json`

Status: `READY_FOR_INDEPENDENT_REVIEW` evidence has now been independently cleared to the reproducibility gate.

Final benchmark manifest: **NOT FROZEN**.

## TERMINAL-BENCH
Benchmark: Terminal-Bench 3.0

Execution: **NOT RUN**.

Execution remains **FORBIDDEN** until Chat4:

1. freezes the exact benchmark revision and task subset/order;
2. verifies A/B/C/D condition-harness isolation and reset semantics;
3. freezes provider/settings/accounting invalidation rules and execution ordering;
4. verifies condition-neutral retry/accounting/caching treatment;
5. preserves the artifact and HIGH-performance reservations;
6. publishes and read-backs the final experiment manifest; and
7. explicitly returns a benchmark-execution clearance verdict.

## NEXT GATE
**CHAT4 — BENCHMARK / MEASUREMENT / REPRODUCIBILITY GATE**

Chat4 is authorized to perform reproducibility preparation and freeze the experiment. This authorization does not itself permit Terminal-Bench execution.

## SUPERSEDED HISTORICAL STATES
The following remain part of provenance and are not erased:

- `BLOCKED_NO_CREDENTIALS_OR_ROUTE`
- `BLOCKED_PROVIDER_ACCOUNTING_INVALID`
- LiteLLM provider-inference failure before explicit OpenAI-compatible provider hint
- earlier pre-provider candidate at `bb1d85c225798ee249e461bff5a7f841fd57e2a9`
- superseded discovery run `33961129462` at `a965157dd6c5c88b604fa1f12da116ba97f0ed66`

## Evidence boundary
Engineering/provider/reviewer gates are now cleared sufficiently to enter Chat4 reproducibility review. They do **not** establish that structured memory improves tokens per success. That claim remains untested until the frozen A/B/C/D Terminal-Bench experiment is executed and independently measured.
