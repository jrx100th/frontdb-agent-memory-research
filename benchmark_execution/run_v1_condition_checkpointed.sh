#!/usr/bin/env bash
set -euo pipefail

TASK_ID="$1"
TASK_ORDER="$2"
CONDITION="$3"
POSITION="$4"
ROOT="$(pwd)"
TB_ROOT="$ROOT/terminal-bench"
RUN_ID="${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${TASK_ORDER}-${CONDITION}"
RUN_ROOT="$ROOT/checkpoints-v1/${TASK_ORDER}-${TASK_ID}/${CONDITION}/${RUN_ID}"
RUNTIME_TASK="$RUN_ROOT/runtime-task"
PREFLIGHT="$RUN_ROOT/preflight-source.json"
JOBS_DIR="$RUN_ROOT/harbor-jobs"
EVIDENCE_DIR="$RUN_ROOT/evidence"
IDENTITY_EVIDENCE="$RUN_ROOT/runtime-identity.json"
RUNTIME_LEDGER="$RUN_ROOT/observed-runtime-image-id.txt"
mkdir -p "$RUN_ROOT"

if [[ ! "$CONDITION" =~ ^[ABCD]$ || ! "$POSITION" =~ ^[1-4]$ ]]; then
  echo "CONFIGURATION_INVALID_V1_TASK_CONDITION_METADATA" >&2
  exit 80
fi

python benchmark_execution/v1_runtime_task.py \
  --image-manifest reproducibility/v1_task_images.json \
  --source-task "$TB_ROOT/tasks/$TASK_ID" \
  --destination "$RUNTIME_TASK" \
  --task "$TASK_ID"

set +e
python benchmark_execution/v1_preflight.py \
  --repo-root "$ROOT" \
  --tb-root "$TB_ROOT" \
  --runtime-task "$RUNTIME_TASK" \
  --run-root "$RUN_ROOT" \
  --task "$TASK_ID" --task-order "$TASK_ORDER" \
  --condition "$CONDITION" --condition-position "$POSITION" \
  --run-id "$RUN_ID" --output "$PREFLIGHT" \
  >"$RUN_ROOT/preflight.stdout.log" 2>"$RUN_ROOT/preflight.stderr.log"
PREFLIGHT_RC=$?
set -e
if [[ $PREFLIGHT_RC -ne 0 ]]; then
  echo "V1_FATAL_PRE_PROVIDER_PREFLIGHT task=$TASK_ID condition=$CONDITION" >&2
  cat "$RUN_ROOT/preflight.stderr.log" >&2 || true
  exit 81
fi

export FROZEN_MANIFEST_SHA256="$(cat reproducibility/V1_MANIFEST_SHA256.txt)"
export FROZEN_ENV_PACKET_SHA256="26566fea65da18291160d2f45598942182d4edf23e1b95485734bc196a67945e"
export FROZEN_STATIC_ENV_PREFLIGHT="PASS"
export FROZEN_TASK_ID="$TASK_ID"
export FROZEN_TASK_IDENTITY_SHA256="$(python -c "import json; print(json.load(open('$PREFLIGHT'))['task_environment_identity_sha256'])")"
export FROZEN_CONDITION="$CONDITION"
export FROZEN_RUN_ID="$RUN_ID"
export FROZEN_TASK_ORDER="$TASK_ORDER"
export FROZEN_CONDITION_POSITION="$POSITION"
export FROZEN_MINI_ARCHIVE="$ROOT/frozen-mini.tar.gz"
export FROZEN_RUNNER_SCRIPT="$ROOT/benchmark_execution/frozen_runner.py"
export FROZEN_PROVIDER_CONSTRAINTS="$ROOT/frozen-build/provider-constraints.txt"
export FROZEN_EXECUTION_HARNESS_SHA="$GITHUB_SHA"
export V1_MANIFEST_PATH="$ROOT/manifests/experiment_manifest.v1.final.json"
export V1_MANIFEST_HASH_RECORD="$ROOT/reproducibility/V1_MANIFEST_SHA256.txt"
export V1_TASK_IMAGE_MANIFEST_PATH="$ROOT/reproducibility/v1_task_images.json"
export V1_TASK_IMAGE_MANIFEST_HASH_RECORD="$ROOT/reproducibility/V1_TASK_IMAGE_MANIFEST_SHA256.txt"
export V1_TASK_ENVIRONMENT_BUNDLE_SHA256="$(python -c "import json; print(json.load(open('$PREFLIGHT'))['task_environment_bundle_sha256'])")"
export V1_RUNTIME_SERVICE_REFS_JSON="$(python -c "import json; print(json.dumps(json.load(open('$PREFLIGHT'))['service_identity'],sort_keys=True,separators=(',',':')))")"
export V1_RUNTIME_IDENTITY_EVIDENCE="$IDENTITY_EVIDENCE"

rm -rf "$JOBS_DIR"
set +e
harbor run \
  --path "$RUNTIME_TASK" \
  --agent benchmark_execution.v1_evidence_agent:V1EvidenceFrozenMiniSweAgent \
  --model z-ai/glm-5.3-free \
  --jobs-dir "$JOBS_DIR" \
  --job-name "frozen-v1-${TASK_ORDER}-${TASK_ID}-${CONDITION}-${RUN_ID}" \
  --n-attempts 1 --n-concurrent 1 --max-retries 0 \
  --no-force-build --delete --yes \
  >"$RUN_ROOT/harbor.stdout.log" 2>"$RUN_ROOT/harbor.stderr.log"
HARBOR_RC=$?
set -e
printf '%s\n' "$HARBOR_RC" > "$RUN_ROOT/harbor.exitcode"

if [[ -s "$IDENTITY_EVIDENCE" ]]; then
  python - "$IDENTITY_EVIDENCE" "$RUNTIME_LEDGER" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
assert x['status']=='PASS'
assert x['provider_calls_before_identity_acceptance']==0
assert x['actual_main_runtime_image_id']==x['expected_main_runtime_image_id']
open(sys.argv[2],'w').write(x['actual_main_runtime_image_id']+'\n')
PY
fi

set +e
PP_ARGS=(
  --jobs-dir "$JOBS_DIR" --preflight "$PREFLIGHT" --task "$TASK_ID" --task-order "$TASK_ORDER"
  --condition "$CONDITION" --condition-position "$POSITION" --run-id "$RUN_ID" --output-dir "$EVIDENCE_DIR"
  --v1-manifest "$ROOT/manifests/experiment_manifest.v1.final.json"
  --v1-manifest-hash "$ROOT/reproducibility/V1_MANIFEST_SHA256.txt"
)
if [[ -s "$RUNTIME_LEDGER" ]]; then
  PP_ARGS+=(--runtime-image-ledger "$RUNTIME_LEDGER")
fi
python benchmark_execution/postprocess_v1.py "${PP_ARGS[@]}" \
  >"$RUN_ROOT/postprocess.stdout.log" 2>"$RUN_ROOT/postprocess.stderr.log"
POST_RC=$?
set -e

mkdir -p "$EVIDENCE_DIR"
cp -f "$RUN_ROOT/harbor.stdout.log" "$RUN_ROOT/harbor.stderr.log" "$RUN_ROOT/harbor.exitcode" "$EVIDENCE_DIR/" 2>/dev/null || true
cp -f "$RUN_ROOT/postprocess.stdout.log" "$RUN_ROOT/postprocess.stderr.log" "$EVIDENCE_DIR/" 2>/dev/null || true
cp -f "$IDENTITY_EVIDENCE" "$RUNTIME_LEDGER" "$EVIDENCE_DIR/" 2>/dev/null || true

if [[ $POST_RC -ne 0 ]]; then
  echo "V1_FATAL_POSTPROCESS task=$TASK_ID condition=$CONDITION" >&2
  cat "$RUN_ROOT/postprocess.stderr.log" >&2 || true
  exit 82
fi

set +e
python - "$EVIDENCE_DIR/run_result.json" "$EVIDENCE_DIR/condition_complete.json" <<'PY'
import json,sys
from benchmark_execution.completion_marker import build_completion_record
r=json.load(open(sys.argv[1]))
if r.get('evaluator_result') is None:
    raise SystemExit(2)
try:
    marker=build_completion_record(r)
except RuntimeError:
    raise SystemExit(3)
open(sys.argv[2],'w').write(json.dumps(marker,sort_keys=True,separators=(',',':'))+'\n')
if not marker.get('continuation_permitted'):
    raise SystemExit(4)
PY
CONTROL_RC=$?
set -e
if [[ $CONTROL_RC -ne 0 ]]; then
  echo "V1_FATAL_CONDITION_CONTROL task=$TASK_ID condition=$CONDITION rc=$CONTROL_RC" >&2
  exit 83
fi

if [[ ! -s "$EVIDENCE_DIR/condition_complete.json" ]]; then
  echo "V1_FATAL_COMPLETION_MARKER_MISSING" >&2
  exit 84
fi

echo "V1_CONDITION_CHECKPOINTED task=$TASK_ID condition=$CONDITION harbor_rc=$HARBOR_RC"
