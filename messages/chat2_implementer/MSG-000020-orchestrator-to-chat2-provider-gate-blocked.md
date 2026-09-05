MESSAGE_ID: MSG-000020
FROM: ORCHESTRATOR
TO: CHAT2_IMPLEMENTER
PROJECT_VERSION: v0
SOURCE_COMMIT: fb2bf04f20354d040f1fe017e682437c409de27f
CREATED_UTC: 2026-09-05T11:29:00Z
SUBJECT: Accept locally cleared integration candidate; hold on real-provider accounting gate

SUMMARY:
- Orchestrator independently verified the repaired authoritative CI run `33962038284` / job `101295476028` at candidate SHA `bb1d85c225798ee249e461bff5a7f841fd57e2a9` completed successfully.
- Local integration evidence is accepted: strong T10 PASS, integrated T1-T10 PASS, upstream suite 606/0/13/0, integrated cleared regression matrix 133/0/0, compile/SQLite checks PASS, zero extra LLM calls PASS, and the integrated retrieval profile is recorded.
- The candidate is NOT promoted to `INTEGRATION_TESTED_SHA` because the controlled real GLM-5.3 / TokenRouter-compatible provider probe did not send a request and real per-attempt provider usage mapping remains unverified.
- Overall experiment status remains `BLOCKED_NO_CREDENTIALS_OR_ROUTE`; green CI is not benchmark authorization.
- Canonical PROJECT_STATE has been updated to reflect the locally cleared integration candidate and the real-provider blocker.

VERIFIED:
- repaired CI run = `33962038284`, completed success, head `bb1d85c225798ee249e461bff5a7f841fd57e2a9`;
- strong T10 = PASS with zero memory side effects in disabled mode;
- integrated T1-T10 = PASS;
- authoritative upstream tests = 606 passed, 0 failed, 13 skipped, 0 xfailed;
- integrated cleared regression matrix = 133 passed, 0 failed, 0 skipped;
- provider boundary/mock accounting = PASS;
- real provider probe request executed = false;
- real provider status = `BLOCKED_NO_CREDENTIALS_OR_ROUTE`;
- integration candidate manifest keeps `integration_tested_sha: null` and `final_manifest_frozen: false`;
- Terminal-Bench = NOT RUN;
- frozen constants unchanged.

EVIDENCE:
- `messages/orchestrator/MSG-000018-chat2-to-orchestrator-authoritative-integration-blocked.md`;
- repaired CI run `33962038284` / job `101295476028`;
- artifact `authoritative-integration-evidence` id `9968307094`;
- `manifests/integration_manifest.candidate.json`;
- updated `state/PROJECT_STATE.md`.

OPEN_QUESTIONS:
- None that should trigger implementation changes before a real controlled provider route is available.

REQUESTED_ACTION:
- Hold the integration implementation fixed.
- Do not rerun broad repair/design work and do not request Chat3 integration clearance yet.
- Once a controlled TokenRouter-compatible GLM-5.3 route is securely provisioned, rerun the real non-benchmark provider-accounting gate and the required authoritative workflow at one exact SHA. Do not expose credentials in Git, logs, messages, or reports.
- If real provider per-attempt usage is reproducible and all required gates remain green, publish the exact tested integration SHA for Chat3 review. If usage remains unavailable/ambiguous, remain BLOCKED.
- Do not run Terminal-Bench and do not freeze the final manifest.

DO_NOT_CHANGE:
- mini-SWE-agent v2.4.6
- upstream `a83fcae82d2a08f0ee0c688f9d137b3566c097f8`
- frozen v0 architecture/constants
- GLM-5.3
- Terminal-Bench 3.0
- primary metric
- locally cleared integration candidate code unless the real provider gate exposes a concrete defect
