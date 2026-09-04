# Frozen Experimental Variables

These variables may not be changed silently. Any proposal to change them must go through the orchestrator and the decision/message audit trail.

| Variable | Frozen value |
|---|---|
| mini-SWE-agent | `v2.4.6` |
| upstream commit | `a83fcae82d2a08f0ee0c688f9d137b3566c097f8` |
| recent_steps | `4` |
| retrieval_budget | `2048` local packing units/tokens, including complete serialized synthetic message |
| max_chunk | `256` local packing units/tokens |
| database | SQLite FTS5 `unicode61` |
| file freshness | SHA-256 referenced-file fingerprinting |
| memory generation | zero extra LLM calls |
| cross-task memory | disabled |
| embeddings | none |
| vector database | none |
| primary metric | provider-reported total tokens / successful tasks |
| benchmark | Terminal-Bench 3.0 |
| benchmark execution | **FORBIDDEN until integration/T10/reproducibility gates pass** |

Local token estimation is for chunking/packing/context safety only and must not be used as the benchmark metric.
