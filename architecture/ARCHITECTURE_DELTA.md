# Architecture Delta

## Current delta from frozen v0

**None intentionally.** The staged implementation is a transfer of the frozen v0 design, not a redesign.

Implementation-state notes that do **not** alter the architecture:

1. The official GLM-5.3 tokenizer revision has not yet been pinned reproducibly, so staging uses the architect-approved conservative fallback: one canonical UTF-8 byte = one local packing unit.
2. The authoritative mini-SWE-agent v2.4.6 checkout has not yet been patched, so baseline equivalence (T10) remains unverified.
3. Provider-attempt accounting for the eventual GLM/TokenRouter route remains unverified end-to-end.

Any future architectural change requires an orchestrator decision and a new audited message/commit; this file must not be used to silently revise frozen variables.
