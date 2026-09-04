# Decisions Ledger

This bootstrap records already-frozen orchestrator decisions. Future canonical decision changes are owned by the ORCHESTRATOR.

## D-001 — Harness revision
- Decision: mini-SWE-agent `v2.4.6`.
- Upstream commit: `a83fcae82d2a08f0ee0c688f9d137b3566c097f8`.
- Status: FROZEN.

## D-002 — Memory core
- Decision: task-local SQLite FTS5 (`unicode61`) memory; no embeddings, vector DB, generated summaries, or extra LLM calls.
- Status: FROZEN.

## D-003 — Context policy
- Decision: system + original task + optional one-user historical-memory message + last 4 complete native steps.
- Baseline memory-disabled mode must preserve native behavior exactly.
- Status: FROZEN.

## D-004 — Retrieval packing
- Decision: historical retrieved memory is capped at 2048 local packing units including the complete serialized synthetic memory message; maximum raw chunk 256 local units.
- Status: FROZEN.

## D-005 — File freshness
- Decision: SHA-256 fingerprints of referenced regular files only, fail closed; no command-parser revision counters.
- Status: FROZEN.

## D-006 — Experimental metric and benchmark gate
- Primary metric: provider-reported total tokens / successfully solved tasks.
- Benchmark: Terminal-Bench 3.0.
- Execution: forbidden until integration, T10, and reproducibility gates pass.
- Status: FROZEN.
