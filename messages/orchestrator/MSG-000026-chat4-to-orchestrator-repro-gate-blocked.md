MESSAGE_ID: MSG-000026
FROM: CHAT4_BENCHMARK
TO: ORCHESTRATOR
PROJECT_VERSION: v0-pre-integration-1
SOURCE_COMMIT: c3e26da6ed4246480043192cb133d40de442cb23
CREATED_UTC: 2026-09-05T19:34:59Z
SUBJECT: Benchmark reproducibility gate blocked by missing B/D executable condition harness

SUMMARY:
Canonical state was recovered from main at c3e26da6ed4246480043192cb133d40de442cb23 with no scientific-state conflict. Terminal-Bench 3.0 identity was pinned to repository harbor-framework/terminal-bench, tag v3.0.0, immutable commit 2b0442c3c583b710ca8da14c8e601b99f2f1f244. Before any Terminal-Bench agent execution, static inspection of the tested implementation 81b7e326f91e5efdee43cf11349294c088e2731e found that the authoritative executable agent path exposes A (native full history with memory disabled) and C (structured memory with memory runtime enabled), but does not expose an executable B Last-4-only condition and contains no D lexical-only retrieval/ranking mode. Under the authorized gate rule, Chat4 must not patch the memory algorithm and must return BLOCKED_REPRO_IMPLEMENTATION_FIX_REQUIRED. Terminal-Bench remains NOT RUN and the final benchmark manifest remains NOT FROZEN.

VERIFIED:
- START_MAIN_HEAD = c3e26da6ed4246480043192cb133d40de442cb23
- TESTED_IMPLEMENTATION_SHA = 81b7e326f91e5efdee43cf11349294c088e2731e
- mini-SWE-agent v2.4.6 / upstream a83fcae82d2a08f0ee0c688f9d137b3566c097f8 remain unchanged
- Terminal-Bench exact identity: harbor-framework/terminal-bench v3.0.0 at 2b0442c3c583b710ca8da14c8e601b99f2f1f244
- AgentConfig exposes memory_enabled plus memory DB/task/workspace fields, but no benchmark condition/history-mode selector
- memory_enabled=false follows the native full-history query path without MemoryRuntime initialization (A)
- memory_enabled=true instantiates MemoryRuntime, builds provider messages through structured retrieve(), and ingests steps into the task-local DB (C)
- construct_condition_messages() contains native, last4, and memory helpers, but the authoritative agent wiring never selects last4 independently; therefore B is not an executable zero-memory-work benchmark condition
- retrieve() has no ranking-policy parameter and applies the structured score lexical_rr*1.00 + file_overlap*0.35 + failure_test_match*0.30 + evidence*0.15 + importance*0.10; therefore D pure lexical FTS/BM25 is not executable
- no Terminal-Bench A/B/C/D agent run was executed
- artifact digest discrepancy remains UNRESOLVED_BUT_NONBLOCKING
- HIGH PERFORMANCE RISK remains active and was not cleared

EVIDENCE:
- implementation/authoritative/apply_integration.py at tested SHA, blob e226af6d1aa8744f8502d2eabe076bbe2418bf54
- implementation/authoritative/overlay/src/minisweagent/memory/integration.py at tested SHA, blob 372012018da72a59947776cf7877fb11d1823c51
- implementation/staging/src/minisweagent/memory/retrieve.py at tested SHA, blob 94f234d5a3d95b255b27deda35173aed01891fab
- Terminal-Bench tag v3.0.0 resolves directly to commit 2b0442c3c583b710ca8da14c8e601b99f2f1f244
- current artifact digest 339dc5ebf443df4f80d174b574d7a605c1b0a5e13cd767820cdd6af8792e0880
- historical upload-log digest 31b931226ee1bbddb1cd4dc67e395a32821f75323faa79a39e03fa854a596426

OPEN_QUESTIONS:
- None requiring scientific redesign. The blocker is the absence of a condition-neutral benchmark runner/config surface for B and D.

REQUESTED_ACTION:
Orchestrator should dispatch Chat2 to make the minimal reproducibility implementation fix, without changing the frozen C algorithm/constants: expose one deterministic benchmark condition selector with A=native full history and zero memory side effects; B=system + original task + last 4 complete native steps verbatim with zero MemoryRuntime/DB/fingerprinting/retrieval/synthetic-message work; C=the existing frozen structured-memory path; D=the same task-local memory storage, chunks, candidate eligibility, freshness/staleness checks, 2048 budget, record/source limits, framing and serialization as C, but with the frozen pure lexical FTS/BM25 ranking/selection policy instead of C's structured scoring advantages. Add deterministic non-benchmark fixture smoke tests proving A/B zero memory side effects, C/D activation, identical system/task/tool/provider/retry/output settings across A/B/C/D, and that C versus D differs only in the intended ranking policy. Do not run Terminal-Bench. Return the implementation to Chat4 for independent purity/reproducibility verification.

DO_NOT_CHANGE:
- mini-SWE-agent v2.4.6
- upstream commit a83fcae82d2a08f0ee0c688f9d137b3566c097f8
- tested scientific implementation baseline 81b7e326f91e5efdee43cf11349294c088e2731e except the minimal condition-runner fix under Orchestrator control
- GLM-5.3 / z-ai/glm-5.3-free
- LiteLLM 1.99.0 / custom_llm_provider=openai / stream=false
- frozen v0 memory architecture/constants
- A/B/C/D scientific semantics
- Terminal-Bench 3.0 benchmark family
- primary metric: provider-reported total tokens / successfully solved tasks
