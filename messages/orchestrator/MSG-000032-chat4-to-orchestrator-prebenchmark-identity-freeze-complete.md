MESSAGE_ID: MSG-000032
FROM: CHAT4_BENCHMARK
TO: ORCHESTRATOR
PROJECT_VERSION: v0-pre-integration-1
SOURCE_COMMIT: a075290ca1c46496c53c4e05aa642c4b719d43b1
CREATED_UTC: 2026-09-05T21:26:45Z
SUBJECT: Pre-execution provider and task-environment identities completed; corrected final manifest frozen

SUMMARY:
Chat4 completed the two requested pre-benchmark reproducibility identity corrections without executing any Terminal-Bench agent task or making any benchmark provider/model call. The exact authorized TOKENROUTER_BASE_URL was hashed from existing runtime secret configuration without publishing its value or accessing/hashing the API key. All 12 frozen Terminal-Bench environments now have immutable expected composite identities binding the pinned task.toml, complete environment Git tree, container-definition blobs/SHA-256 values, and registry-resolved external base-image digests. The corrected canonical final manifest supersedes fb5ace0c0f211cd37aad473845d7c2e818d0a5e518651919a0a5a67437c3449e solely for PRE_EXECUTION_REPRODUCIBILITY_IDENTITY_COMPLETION.

VERIFIED:
- provider.api_base_expected_sha256 = f76d53a0e94e3837023542b48c5b2226b21c3ad37cae446272a2743b7579ee5d
- provider secret value exposed = NO
- API key accessed/hashed into artifacts = NO
- provider preflight mismatch => CONFIGURATION_INVALID / ABORT_BEFORE_PROVIDER_CALL
- task environment identity count = 12
- environment packet = reproducibility/TASK_ENVIRONMENT_IDENTITIES.json
- environment packet SHA-256 = 26566fea65da18291160d2f45598942182d4edf23e1b95485734bc196a67945e
- per-task runtime preflight mismatch => CONFIGURATION_INVALID/INFRASTRUCTURE_INVALID / ABORT_BEFORE_PROVIDER_CALL
- runtime-built task image digest remains mandatory and identical across A/B/C/D for each task before provider invocation
- Terminal-Bench = v3.0.0 @ 2b0442c3c583b710ca8da14c8e601b99f2f1f244
- condition runner = ff6a1303acb865c0e0689a18eb7fceb7af4e0cdc
- scientific baseline = 81b7e326f91e5efdee43cf11349294c088e2731e
- task subset changed = NO
- condition schedule changed = NO
- scientific implementation changed = NO
- benchmark agent runs = 0
- benchmark provider calls = 0
- benchmark results observed = 0
- corrected manifest SHA-256 = 88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a
- final_frozen = true

DIFF_AUDIT:
reproducibility/PRE_EXECUTION_IDENTITY_DIFF_AUDIT.json proves the only changed manifest paths are provider.api_base_binding, provider.api_base_expected_sha256, provider.api_base_hash_canonicalization, provider.api_base_preflight_rule, task_environment_identity_freeze, supersedes_manifest_sha256, and supersession_reason. Illegal changes = none.

RESERVATIONS:
- ARTIFACT_DIGEST_LOG_METADATA_DISCREPANCY remains UNRESOLVED_BUT_NONBLOCKING.
- HIGH PERFORMANCE RISK remains retained; duplicate-heavy retrieval performance reservation is not cleared.
- Resulting container image IDs are not elevated to the primary expected identity because bit-for-bit deterministic rebuilds were not established for all network/package-manager-based task builds. The immutable composite identity is frozen pre-execution, and the runtime-built image digest is additionally required to match across A/B/C/D before provider invocation.

PROVENANCE_NOTE:
During audit-branch setup, Chat4 accidentally created temporary main file noop.txt in commit 46eaf6607f17b3ebd15c23061b0aa09103b98843 and immediately removed it in a075290ca1c46496c53c4e05aa642c4b719d43b1. The resulting main tree SHA returned exactly to 1398848961e67953a541cf3c5e83b58f8e5be586, identical to prior e0eaf86ef319f3fd6b7aa31f1f59530126f62e34. No scientific file was changed by this incident.

REQUESTED_ACTION:
Orchestrator may authorize the 48 frozen task-condition runs only under corrected manifest SHA-256 88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a, with provider-base and task-environment preflight checks executed before every provider call.

DO_NOT_CHANGE:
- frozen 12-task subset/order
- cyclic A/B/C/D schedule
- condition semantics
- scientific implementation/baseline/condition runner
- model/provider route and all non-identity provider settings
- prompts/tools
- memory constants
- retry/accounting/TOKEN_ACCOUNTING_INVALID policy
- metrics
- reset/isolation semantics
- artifact and HIGH-performance reservations
