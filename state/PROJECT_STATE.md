# Project State

## PROJECT
Agent Memory Efficiency Experiment

## STATUS
V0 architecture frozen.
Staging independently cleared.
Authoritative mini-SWE-agent v2.4.6 integration candidate is implemented and locally validated at `bb1d85c225798ee249e461bff5a7f841fd57e2a9`.

The experiment is **BLOCKED** on the controlled real GLM-5.3 / TokenRouter-compatible per-attempt provider-usage gate.

No final `INTEGRATION_TESTED_SHA` is claimed.

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

## LOCALLY VERIFIED AUTHORITATIVE INTEGRATION EVIDENCE
- exact upstream v2.4.6 identity at `a83fcae82d2a08f0ee0c688f9d137b3566c097f8` verified;
- repaired authoritative CI run `33962038284` / job `101295476028` completed successfully at candidate SHA `bb1d85c225798ee249e461bff5a7f841fd57e2a9`;
- strong T10 PASS: pristine upstream vs patched `memory_enabled=false` provider request/config/tool structure equivalent, with zero memory runtime/DB/fingerprint/retrieval/context/synthetic-message side effects;
- integrated T1-T10 PASS;
- authoritative upstream suite: 606 passed, 0 failed, 13 skipped, 0 xfailed;
- integrated cleared regression matrix: 133 passed, 0 failed, 0 skipped;
- provider-attempt boundary and controlled mock retry/parse-failure accounting PASS; missing/malformed usage fails closed and no local estimator is substituted;
- zero extra LLM calls PASS;
- integrated retrieval profile recorded: ~5 rows `0.003702 s`, ~100 `0.004949 s`, ~1000 `0.021594 s`, ~10000 `0.172598 s` for that profile distribution;
- frozen experimental constants unchanged.

## SUPERSEDED DISCOVERY RUN
Run `33961129462` at `a965157dd6c5c88b604fa1f12da116ba97f0ed66` is not final scientific evidence. It exposed two patch-caused upstream regressions and lacked a real provider route. Those regressions were repaired before the full rerun above.

## BLOCKED / NOT VERIFIED
- the controlled real TokenRouter-compatible GLM-5.3 probe did not issue an API request because its environment lacked configured API key, base URL, and model route;
- real per-attempt provider usage object shape and mapping remain UNVERIFIED;
- provider input/output/total/cached/reasoning field behavior remains UNVERIFIED on the real route;
- `integration_tested_sha` remains null / NOT CLAIMED;
- independent Chat3 authoritative-integration review is deferred until the real-provider gate resolves.

## PERFORMANCE RESERVATION
- prior ~8.91 s / ~10k exact-duplicate adversarial stress remains **HIGH PERFORMANCE RISK**;
- the newer ~0.172598 s / 10k integrated profile is a different distribution and does not invalidate the earlier reservation;
- no latency threshold is frozen.

## MANIFEST
Candidate: `manifests/integration_manifest.candidate.json` updated.

Final manifest: **NOT FROZEN**.

## TERMINAL-BENCH
**NOT RUN**

**FORBIDDEN** until the real provider-accounting gate resolves, an exact integration SHA is independently reviewed, and the benchmark/reproducibility gate passes.

## Evidence boundary
Green CI proves the locally executable integration gates only. It does **not** clear the real-provider scientific accounting gate and does not authorize Terminal-Bench.
