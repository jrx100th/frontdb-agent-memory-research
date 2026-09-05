# Project State

## PROJECT
Agent Memory Efficiency Experiment

## STATUS
V0 architecture frozen.
Staging implementation is **CLEARED FOR AUTHORITATIVE INTEGRATION WITH RESERVATIONS** by independent Chat3 review.
Implementation is still **NOT integrated** into the authoritative mini-SWE-agent checkout.

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

## CURRENT VERIFIED STAGING EVIDENCE
- Chat2 exact repair CI at `f7bd4125c463f3d79c4e0094fdedca7c86680b06`: 133 pytest cases PASS, 0 fail, 0 skip; compileall PASS; SQLite FTS5 PASS; SQLite `integrity_check=ok`.
- Focused independent Chat3 command-equivalence clearance: PASS_WITH_RESERVATIONS.
- Independent reviewer CI run `33959539227` / job `101288875042`: 21/21 new focused command cases PASS, 20/20 command regressions PASS, 21/21 previously-cleared retrieval/freshness spot checks PASS.
- C03 shell-distinct command-equivalence defect is cleared.
- Previously-cleared R01/R05/R06B/R11/R13/R17/R27 and A03/A07/A08/A09-A12 remain cleared for staging scope.
- Frozen experimental constants unchanged.

## AUTHORIZATION
**PROCEED TO AUTHORITATIVE INTEGRATION** of the cleared staging implementation into exact mini-SWE-agent v2.4.6 at upstream commit `a83fcae82d2a08f0ee0c688f9d137b3566c097f8`.

The integration gate must include:
- integrated T1-T10;
- strong T10 native disabled-path equivalence;
- upstream mini-SWE-agent regression tests;
- provider-attempt usage capture/aggregation integration;
- GLM/TokenRouter usage-shape validation;
- retrieval-latency profiling, especially the previously observed ~8.91 s / ~10k lexical-match stress case.

## RESERVATIONS CARRIED INTO INTEGRATION
- HIGH PERFORMANCE RISK: large same-term lexical-match histories; ~8.91 s observed at ~10k matches in staging stress testing.
- malformed legacy JSON remains a fail-loud migration robustness risk.
- provider-attempt aggregation and actual GLM/TokenRouter usage mapping remain integration gates.
- baseline equivalence remains unverified until strong T10 passes.

## NOT VERIFIED
- T10 native disabled equivalence.
- authoritative patched mini-SWE-agent checkout.
- upstream mini-SWE-agent tests under the integrated patch.
- GLM/TokenRouter provider-attempt usage integration and mapping.
- integrated retrieval latency/profile behavior.

## FINAL MANIFEST
**NOT FROZEN**

Final manifest must not be frozen before the authoritative integration gate passes at one exact implementation commit.

## TERMINAL-BENCH
**NOT RUN**

**FORBIDDEN** until authoritative integration, strong T10, upstream/provider-accounting checks, and Chat4 reproducibility gate pass.

## Evidence boundary
Staging clearance authorizes integration only. It is not evidence that the authoritative mini-SWE-agent integration is correct, baseline-equivalent, provider-accounting-valid, or benchmark-ready.
