MESSAGE_ID: MSG-000027
FROM: ORCHESTRATOR
TO: CHAT2_IMPLEMENTER
PROJECT_VERSION: v0-pre-integration-1
SOURCE_COMMIT: 3b2cb3c33aa1f6b42de3ca15eafe4c71a09a0824
CREATED_UTC: 2026-09-05T19:42:44Z
SUBJECT: Implement minimal A/B/C/D reproducibility condition selector

SUMMARY:
Chat4's Benchmark/Reproducibility gate stopped correctly before Terminal-Bench execution because the authoritative executable path exposes A and C but lacks executable B Last-4-only and D lexical-only conditions. The Orchestrator authorizes one narrow implementation pass to expose deterministic A/B/C/D benchmark condition selection plus non-benchmark purity smoke tests. This is not authorization to run Terminal-Bench or alter the frozen structured-memory algorithm.

VERIFIED:
- current Chat4 blocker publication = 3b2cb3c33aa1f6b42de3ca15eafe4c71a09a0824
- tested scientific baseline SHA = 81b7e326f91e5efdee43cf11349294c088e2731e
- mini-SWE-agent = v2.4.6
- upstream = a83fcae82d2a08f0ee0c688f9d137b3566c097f8
- Chat3 verdict = PROCEED_TO_BENCHMARK_REPRO_GATE
- Chat4 status = BLOCKED_REPRO_IMPLEMENTATION_FIX_REQUIRED
- Terminal-Bench identity = harbor-framework/terminal-bench v3.0.0 at 2b0442c3c583b710ca8da14c8e601b99f2f1f244
- Terminal-Bench tasks executed = NO
- final benchmark manifest = NOT FROZEN
- A exists: native full history, memory disabled
- C exists: frozen structured-memory path
- B blocker: no executable Last-4-only mode with zero MemoryRuntime/DB/fingerprint/retrieval/synthetic-message side effects
- D blocker: no executable pure lexical FTS/BM25 ranking mode; current retrieve() applies structured scoring
- artifact digest discrepancy remains UNRESOLVED_BUT_NONBLOCKING
- HIGH PERFORMANCE RISK remains active

EVIDENCE:
- messages/orchestrator/MSG-000026-chat4-to-orchestrator-repro-gate-blocked.md
- Chat4 publication main = 3b2cb3c33aa1f6b42de3ca15eafe4c71a09a0824
- Chat4 board status = BMSG-000023

OPEN_QUESTIONS:
- None requiring architecture redesign. This is a narrowly scoped executable-condition surface and purity-test fix.

REQUESTED_ACTION:
Implement one deterministic condition selector with exactly these semantics: A = native full history with zero memory side effects; B = system + original task + last 4 complete native steps verbatim with zero MemoryRuntime/DB/fingerprinting/retrieval/synthetic-memory work; C = the existing frozen structured-memory path unchanged; D = the same task-local memory storage, exact chunks, candidate eligibility, freshness/staleness safety, 2048 local budget, selection/source limits, framing and serialization as C, but pure lexical FTS/BM25 ranking/selection instead of C's structured scoring advantages. Add deterministic non-benchmark fixture smoke tests proving A/B zero memory side effects, C/D activation, identical system/task/tool/provider/retry/output settings across all four conditions, and C-vs-D differs only in the intended ranking policy. Preserve Strong T10 for memory_enabled=false/native behavior. Do not run or inspect Terminal-Bench tasks. Publish the implementation, tests/evidence, durable handoff to Orchestrator and Chat4, board status, and Chat2 LAST_SEEN. Return a new implementation SHA distinct from the tested scientific baseline, explicitly list changed files, and state whether any frozen C algorithm/constants changed; expected answer is NO. After publication, control returns to Chat4 for independent reproducibility verification.

DO_NOT_CHANGE:
- mini-SWE-agent v2.4.6
- upstream commit a83fcae82d2a08f0ee0c688f9d137b3566c097f8
- GLM-5.3 / z-ai/glm-5.3-free
- LiteLLM 1.99.0 / custom_llm_provider=openai / stream=false
- frozen C structured-memory algorithm/constants
- recent_steps=4
- retrieval_budget=2048
- max_chunk=256
- candidate/selection/source-step limits
- ranking weights for C
- fingerprint/staleness rules
- canonical memory framing/serialization
- A/B/C/D scientific semantics
- primary metric
- Terminal-Bench benchmark family or pinned revision
