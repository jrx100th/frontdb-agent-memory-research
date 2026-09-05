# Chat4 Independent Condition-Harness Reproducibility Review V0

ROLE: CHAT 4 — BENCHMARK / MEASUREMENT / REPRODUCIBILITY

START_MAIN_HEAD: `eec95f45132f9741234865d8a2f11eae3503ad81`
BASELINE_SHA: `81b7e326f91e5efdee43cf11349294c088e2731e`
CONDITION_RUNNER_SHA: `ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc`
TERMINAL-BENCH AGENT TASKS: **NOT RUN**

## Verdict

**READY_TO_EXECUTE_BENCHMARK**

This clears benchmark execution only under the final frozen manifest. It does not establish that structured memory improves efficiency.

## Independent findings

### Canonical state and diff
Canonical main matched the authorized dispatch state; `MSG-000029`, `MSG-000030`, and Issue #1 `BMSG-000026` were processed. No scientific-state conflict was found.

Independent comparison `81b7e326f91e5efdee43cf11349294c088e2731e` -> `ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc` changed exactly:
1. `.github/workflows/chat2-authoritative-integration.yml`
2. `implementation/authoritative/apply_condition_runner.py`
3. `tests/integration/test_condition_runner.py`

No frozen C source/constants changed.

### A — full native history
**PASS.** A uses native complete history and never initializes `MemoryRuntime`; no memory DB, retrieval, fingerprinting, ingest, or synthetic memory path is reachable.

### B — Last-4
**PASS.** B uses system + original task + last four complete native assistant/tool-observation groups. Incomplete trailing groups are excluded and retained messages remain verbatim. B never initializes `MemoryRuntime`; no DB/retrieval/fingerprinting/synthetic-memory work is reachable.

### C — structured memory
**PASS / UNCHANGED.** The repair does not change frozen write policy, schema, ranking coefficients, eligibility, candidate limits, dedup/conflict handling, freshness/fingerprinting, 2048 budget, record/source-step limits, framing, serialization, or verification semantics.

### D — lexical-only
**PASS.** D shares C's task-local storage, chunks, write policy, eligibility, freshness/safety, conflict/dedup, 2048 budget, record/source-step limits, framing, and serialization. D's selection score is only reciprocal primary FTS5/BM25 lexical rank. File-overlap, failure/test, evidence, and importance bonuses are absent. Supplemental-only/nonlexical candidates have zero lexical score and are rejected from D selection.

### Condition neutrality
**PASS.** Prompt/task templates, tool schema, action parsing, provider route/transport, provider accounting, retry/parse-failure behavior, environment execution, and termination behavior were not changed by the repair. Only the frozen history/memory treatment varies.

### Accounting
**PASS.** Provider usage remains captured immediately after response receipt and before action parsing; retries and parse-failed attempts remain auditable; cached tokens are not subtracted; reasoning is not double-counted; missing/malformed usage fails closed; local estimates cannot substitute.

A real non-benchmark probe in the reviewed evidence was `COUNTED` with input `186`, output `36`, total `222`, cached `0`, reasoning `22`; `186 + 36 = 222`.

## Independent evidence verification

Chat4 did not accept Chat2's summary counts alone. Exact changed source/tests/workflow were inspected and the raw CI artifact was independently downloaded and recomputed.

- CI run/job: `33988970398` / `101367636620`
- downloaded evidence ZIP SHA-256: `07c8c5c9ac8f8657d0e12599ff722fb99f1c4b218d94ff45fe71deabcfd515e9`
- raw upstream JUnit independently parsed: `619` tests = **606 passed**, `13 skipped`, `0 failures`, `0 errors`
- Strong-T10 JSON independently inspected: pristine/patched provider-boundary evidence byte-identical; all disabled-path DB/retrieval/fingerprint/memory-import/synthetic-message sentinels passed
- raw evidence records condition purity `10 passed`, integrated suite `18 passed`, provider-accounting mocks `3 passed`, cleared staging/regression `133 passed`, compileall PASS
- Terminal-Bench agent tasks: **NOT RUN**

## Terminal-Bench identity

**PASS.** `harbor-framework/terminal-bench`, tag `v3.0.0`, immutable revision `2b0442c3c583b710ca8da14c8e601b99f2f1f244`. Task selection used pinned task metadata only. No solution/reference-answer material was inspected.

## Frozen execution packet

The self-contained machine-readable packet is `manifests/experiment_manifest.final.json`.

It freezes:
- 12 task IDs and fixed order;
- deterministic 12-task cyclic A/B/C/D schedule (each condition appears exactly three times in each ordinal position);
- A/B/C/D semantics and all memory constants;
- exact provider route/transport/LiteLLM identity plus explicit omitted/provider-default generation settings;
- retry/accounting-invalid/failure rules;
- reset/isolation rules;
- success evaluator;
- primary/secondary metrics;
- per-run output/evidence schema;
- artifact and HIGH-performance reservations.

Manifest SHA-256: `fb5ace0c0f211cd37aad473845d7c2e818d0a5e518651919a0a5a67437c3449e`.

## Performance reservation

**HIGH PERFORMANCE RISK — RETAINED.** Latest evidence: ordinary 10k-row retrieval approximately `0.172640 s`; exact-duplicate 10k-row stress approximately `20.129165 s`. Classification: **FEASIBLE_WITH_RESERVATION**; no benchmark-timeout incompatibility has been demonstrated. Retrieval-induced runtime/timeout during benchmark execution is a condition outcome, not a selective-exclusion reason.

## Artifact reservation

`ARTIFACT_DIGEST_LOG_METADATA_DISCREPANCY` remains **UNRESOLVED_BUT_NONBLOCKING**:
- current API/downloaded-byte digest `339dc5ebf443df4f80d174b574d7a605c1b0a5e13cd767820cdd6af8792e0880`
- historical upload-log digest `31b931226ee1bbddb1cd4dc67e395a32821f75323faa79a39e03fa854a596426`

## Triple check

A — correctness: **PASS**. Exact runner, benchmark revision, tasks/order, schedule, provider packet, isolation, accounting rules, metrics and output schema are frozen.

B — adversarial validity: **PASS_WITH_RESERVATIONS**. No path found for hidden B memory work, D nonlexical supplemental selection, condition-specific retry/accounting exclusion, cross-task/condition memory, adaptive task replacement, or adaptive condition ordering.

C — experimental consistency: **PASS**. A/B/C/D share prompt/tool/provider/accounting/environment/termination behavior and differ only by the frozen history/memory treatment.

## Final decision

**READY_TO_EXECUTE_BENCHMARK**

Terminal-Bench remains **NOT RUN** at publication. Do not alter the final manifest without creating a new experiment version.
