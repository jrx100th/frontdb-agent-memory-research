# Project State

## PROJECT
Agent Memory Efficiency Experiment

## STATUS
V0 architecture frozen.
Implementation staged but **NOT integrated** into authoritative mini-SWE-agent checkout.

## HARNESS
mini-SWE-agent v2.4.6

## UPSTREAM COMMIT
`a83fcae82d2a08f0ee0c688f9d137b3566c097f8`

## MODEL
GLM-5.3

## BENCHMARK
Terminal-Bench 3.0

**NOT RUN**

## PRIMARY METRIC
provider-reported total tokens / successfully solved tasks

## CURRENT VERIFIED IMPLEMENTATION EVIDENCE
- 37 deterministic staging tests PASS.
- T1-T9 staging behavior PASS.
- T5a-T5h PASS.
- Additional adversarial tests PASS.
- `compileall` PASS.
- SQLite FTS5 available.
- SQLite `integrity_check` = `ok`.

## NOT VERIFIED
- T10 native disabled equivalence.
- upstream mini-SWE-agent tests.
- actual patched upstream checkout.
- GLM/TokenRouter provider-attempt usage integration.

## FINAL MANIFEST
**NOT FROZEN**

## TERMINAL-BENCH
**NOT RUN**

## Evidence boundary
The staging results above are isolated deterministic implementation evidence only. They are not evidence that the authoritative mini-SWE-agent integration is correct, baseline-equivalent, or benchmark-ready.
