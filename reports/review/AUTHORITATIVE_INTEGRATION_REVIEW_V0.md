# Chat3 Authoritative-Integration Review V0

ROLE: CHAT 3 — ADVERSARIAL REVIEWER AND FAILURE ANALYST

PROJECT_VERSION: v0-pre-integration-1

REVIEW_START_MAIN_HEAD: `56d7b862811edb7af3dbbfde08215449a70943b7`

TESTED_IMPLEMENTATION_SHA: `81b7e326f91e5efdee43cf11349294c088e2731e`

PUBLICATION_HANDOFF_SHA_REVIEWED: `56d7b862811edb7af3dbbfde08215449a70943b7`

UPSTREAM: mini-SWE-agent v2.4.6 at `a83fcae82d2a08f0ee0c688f9d137b3566c097f8`

MODEL_ROUTE: `z-ai/glm-5.3-free`

PROVIDER_COMPATIBILITY: `custom_llm_provider="openai"`

LITELLM: `1.99.0`

TERMINAL-BENCH: **NOT RUN**

FINAL BENCHMARK MANIFEST: **NOT FROZEN**

## Verdict

**PROCEED_TO_BENCHMARK_REPRO_GATE**

Confidence: 98%.

This verdict authorizes only the Chat4 Benchmark/Reproducibility gate. It does not authorize Terminal-Bench execution.

## Authoritative implementation CI

Authoritative implementation CI reviewed:

- run: `33970854793`
- job: `101318983117`
- head: `81b7e326f91e5efdee43cf11349294c088e2731e`
- conclusion: `success`

The scientific verdict was not inferred from green CI alone.

## Independent Chat3 reviewer CI

Reviewer CI is a separate reviewer-branch object and must not be confused with the tested implementation SHA:

- run: `33983684722`
- job: `101353282558`
- head: `ee42f1cf36a6747410e13c16ddf386af34f98c52`
- conclusion: `success`

Correct command-level results:

- Chat3 adversarial reviewer tests: **14 passed**
- Provider accounting + adapter tests: **13 passed**
- Strong T10: **PASS**
- compileall: **PASS**

No aggregate count is asserted because the command groups are separate and may overlap in purpose.

## Scientific drift

**NO.**

The provider-repair diff from `bb1d85c225798ee249e461bff5a7f841fd57e2a9` to tested implementation `81b7e326f91e5efdee43cf11349294c088e2731e` was restricted to:

1. `.github/workflows/chat2-authoritative-integration.yml`
2. `implementation/authoritative/provider-constraints.txt`
3. `tests/integration/provider_probe.py`
4. `tests/integration/test_provider_adapter.py`

No memory write policy, retrieval, ranking, dedup, fingerprinting, context construction, serialization, frozen retrieval constants, A/B/C/D semantics, benchmark definition, or primary metric changed.

## Provider root cause and adapter

The reviewed evidence supports the claimed route compatibility root cause: raw LiteLLM provider inference for `z-ai/glm-5.3-free` failed, while explicit `custom_llm_provider="openai"` enabled OpenAI-compatible transport while preserving provider-facing model `z-ai/glm-5.3-free`.

No model substitution, fallback model/provider, prompt substitution, tool-schema substitution, or benchmark-specific special casing was found.

## Provider accounting

Final authoritative provider observation:

- input / prompt tokens: **186**
- output / completion tokens: **50**
- total tokens: **236**
- `prompt_tokens_details.cached_tokens`: **0**
- `completion_tokens_details.reasoning_tokens`: **36**

Consistency: **PASS**, because `186 + 50 = 236`.

Final probe state:

- `response_received=true`
- `parse_success=true`
- `stream=false`
- `accounting_status=COUNTED`
- attempted provider calls: `1`
- countable provider calls: `1`
- extra provider calls: `0`

Accounting review: **PASS**.

The implementation records provider usage before action parsing, counts generated/retry attempts, fails closed on missing or malformed usage, does not substitute local token estimates, does not subtract cached tokens from provider totals, does not double-count reasoning tokens, preserves raw usage for audit, and does not hide parse-failed provider attempts.

## Usage provenance

Disposition: **SUPPORTED_WITH_EXPLICIT_SUPERSESSION**.

Historical observations were not averaged or silently rewritten:

- earlier: `187 / 78 / 265`, cached `0`, reasoning `65`
- later intermediate summary: `186 / 50 / 236`, cached `0`, reasoning `37`
- final authoritative artifact: `186 / 50 / 236`, cached `0`, reasoning `36`

The final artifact read supports the final value. Earlier observations remain explicit superseded provenance. The exact cause of the intermediate reasoning-token `37 -> 36` difference was not independently established and remains a nonblocking provenance reservation.

## Artifact integrity

Artifact:

- id: `9970944939`
- name: `authoritative-integration-evidence`
- current GitHub API/downloaded-byte SHA-256: `339dc5ebf443df4f80d174b574d7a605c1b0a5e13cd767820cdd6af8792e0880`
- historical workflow upload-log digest: `31b931226ee1bbddb1cd4dc67e395a32821f75323faa79a39e03fa854a596426`

Disposition: **UNRESOLVED_BUT_NONBLOCKING**.

The two digest observations differ. No explanation was invented and the discrepancy is not cleared. The current artifact API identity and downloaded bytes agree on the current digest, and the candidate manifest preserves the discrepancy rather than hiding it. No evidence-integrity contradiction sufficient to block the next reproducibility gate was demonstrated.

## Strong T10

**STRONG_T10_VERIFIED**.

With `memory_enabled=false`, reviewed evidence established provider-facing native messages/config/tool structure equal to pristine upstream; no synthetic memory message; no memory-runtime/database initialization; no DB reads/writes; no fingerprinting/retrieval/context synthesis on the disabled path. Pristine and patched disabled-path request artifacts were canonically identical.

## Regression review

**PASS.**

No previously fixed historical failure class was shown to reappear in the tested provider repair, including:

- A01 duplicate candidate starvation
- A02 old explicit error recall
- A03 hypothesis/evidence numeric near-dedup
- A04 outcome-conflict dedup
- A05 symlink-retarget TOCTOU / ABA protection
- A06 Unicode mismatch handling
- A07 impossible provider total
- A08 nested cached/reasoning audit
- A09 64 MiB boundary
- A10 whole-message budget
- A11 step grouping
- A12 missing usage
- C03 raw-command identity

## Staleness review

**PASS.**

Fail-closed behavior remained supported for ordinary mutation, same-size mutation with restored mtime, deletion, rename/replacement, symlink target change, >64 MiB, unreadable files, outside-workspace paths, nonregular files, files changing during hash, and duplicate path handling. Current-state `STALE`/`UNKNOWN` is not treated as proof. Historical failure/error records may survive only with stale labeling.

## Retrieval and memory safety

Disposition: **PASS_WITH_RESERVATIONS**.

Supported properties include task-only isolation, recent-4 exclusion, candidate limits, dedup/source-step limits, exact serialized budget enforcement, structural containment of retrieved data, no synthetic memory message on empty retrieval, evidence-status handling, stale current-state exclusion, failed-approach retention, no cross-task contamination, and zero extra LLM calls.

No evidence showed a simple Last-4 mechanism masquerading as structured-memory behavior. Chat4 must still verify condition-harness isolation/order/reset semantics before any benchmark execution.

## Secret review

**PASS.**

No API key, Authorization/Bearer header, cookie, secret environment value, or uploaded raw request header was found in the reviewed provider changes/evidence. No secret material is reproduced here.

## Performance reservation

Classification: **NONBLOCKING_PERFORMANCE_RISK**.

The historical HIGH performance reservation remains. Duplicate-heavy adversarial retrieval has shown materially higher latency than ordinary distributions, and the current evidence does not justify clearing that reservation. There is no frozen latency threshold and no demonstrated benchmark-timeout incompatibility, so this is not presently a scientific-validity blocker. Chat4 must retain and evaluate the reservation during reproducibility/feasibility checks.

## Experimental confounds retained for Chat4

Chat4 must explicitly verify that:

1. resolution rate is reported alongside token efficiency;
2. only frozen memory/history treatment differs across A/B/C/D;
3. retry/accounting rules are condition-neutral;
4. provider caching remains auditable;
5. context truncation differences arise only from the frozen treatment;
6. synthetic-memory framing is included in provider token totals;
7. task and condition ordering cannot contaminate conditions;
8. D lexical-only differs only by the frozen ranking/memory policy;
9. C cannot retrieve information unavailable at that historical step;
10. pristine full-history baseline is not patched differently;
11. Last-4 does not accidentally trigger memory DB/fingerprint work;
12. `TOKEN_ACCOUNTING_INVALID` outcomes cannot be silently discarded to improve a condition.

No blocker was demonstrated at this review gate, but these remain mandatory reproducibility checks.

## Candidate manifest review

Disposition: **PASS_WITH_RESERVATIONS**.

`manifests/integration_manifest.candidate.json` accurately records the tested implementation SHA, exact upstream, provider route/model, LiteLLM version, provider usage mapping/final observation, superseded provenance, artifact-digest discrepancy, test evidence, unchanged frozen constants, Terminal-Bench `NOT_RUN`, HIGH performance reservation, and unchanged primary metric.

It remains a candidate integration manifest, not the final frozen benchmark manifest.

## Critical findings

None meeting `BLOCK_PROVIDER_ACCOUNTING`, `FIX_THEN_REREVIEW`, `REVERT`, or `CORE_REDESIGN_REQUIRED` threshold.

No `SCIENTIFIC_STATE_CONFLICT` was found.

## Nonblocking findings / reservations

- artifact digest discrepancy remains **UNRESOLVED_BUT_NONBLOCKING**;
- historical/intermediate provider usage observations remain explicit superseded provenance;
- exact reason for reasoning-token `37 -> 36` change remains unverified;
- HIGH performance reservation remains active;
- benchmark feasibility under realistic task histories remains for Chat4;
- final benchmark manifest is **NOT FROZEN**;
- Terminal-Bench is **NOT RUN**.

## Triple self-check

### CHECK A — CORRECTNESS

PASS. Scientific PASS claims were grounded in the completed independent review evidence, implementation source/artifact inspection, authoritative CI, or independent reviewer CI; they were not accepted merely from Chat2 assertion.

### CHECK B — ADVERSARIAL

PASS. The completed review attacked accounting failure paths, retry/parse-failure leakage, provider substitution, artifact/provenance discrepancies, staleness, task leakage, recent-4/budget limits, injection containment, C03, performance evidence, and experimental confounds.

### CHECK C — EXPERIMENTAL CONSISTENCY

PASS_WITH_GATE_RESERVATIONS. No tested provider repair introduced scientific drift across A/B/C/D. Chat4 must still certify condition-order/reset and reproducibility semantics before benchmark execution.

## Final decision

**VERDICT: PROCEED_TO_BENCHMARK_REPRO_GATE**

Next action: Orchestrator should update canonical project state and authorize Chat4's Benchmark/Reproducibility gate against exact tested implementation `81b7e326f91e5efdee43cf11349294c088e2731e`, while preserving every reservation above.

Do not change mini-SWE-agent v2.4.6, upstream `a83fcae82d2a08f0ee0c688f9d137b3566c097f8`, GLM-5.3 / `z-ai/glm-5.3-free`, frozen v0 architecture/constants, A/B/C/D semantics, Terminal-Bench 3.0, or the primary metric.
