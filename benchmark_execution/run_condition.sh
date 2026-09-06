#!/usr/bin/env bash
set -euo pipefail

TASK_ID="$1"
TASK_ORDER="$2"
CONDITION="$3"
POSITION="$4"
EXPECTED_IMAGE_DIGEST="${5:-}"
ROOT="$(pwd)"
TB_ROOT="$ROOT/terminal-bench"
RUN_ID="${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${TASK_ORDER}-${CONDITION}"
RUN_ROOT="$ROOT/checkpoints/${TASK_ORDER}-${TASK_ID}/${CONDITION}/${RUN_ID}"
PREFLIGHT="$RUN_ROOT/preflight-source.json"
JOBS_DIR="$RUN_ROOT/harbor-jobs"
EVIDENCE_DIR="$RUN_ROOT/evidence"
IMAGE_LEDGER="$ROOT/runtime-image-${TASK_ORDER}-${TASK_ID}.txt"
mkdir -p "$RUN_ROOT"

case "$TASK_ID" in
  atrx-vep-crispr) TASK_IDENTITY="7cfea578937dbd2103305419aea6391953838e40d33e87b04ce711b4f3432079" ;;
  batched-eval-parity) TASK_IDENTITY="b6331007ec8e73d94acf2ae4814b4a53c91013d22aaa972715d9a6c36e7f7ff4" ;;
  cad-model) TASK_IDENTITY="c3bc1a255c8d5218de9c535b0f8b5b2958f60f6bbe8f51c60fceb98c9d8ff8fb" ;;
  cargo-flight-dispatch) TASK_IDENTITY="05a43221d49b447a0456b121e3a598074fd4d244ebbde5cc3d9092a8e6148035" ;;
  coq-block-bound) TASK_IDENTITY="f4e6770542653e512f9e118d102b0f095f5bfc34fc3e4d870a89812949d49b6d" ;;
  cumulative-layout-shift) TASK_IDENTITY="904c8c50a5c32081ec5001fc6242383ebf008feec7f4a91324faa8c857c50c9a" ;;
  data-anonymization) TASK_IDENTITY="97befd9b118867c57e12b62ee557e3ef651e1e5a9cb7b2be8a0c0ad6c8c9a4c6" ;;
  live-database-cutover) TASK_IDENTITY="0b0815f5dd50877a8ee736508dedc760f45de405adcd96b0209bf8f3467dc82d" ;;
  music-harmony) TASK_IDENTITY="47f348720c5973a7f67b701c8c177215bf1e73e0a1f97f1fef2606a824d36619" ;;
  uefi-bootkit) TASK_IDENTITY="d6c0a9df1bc1fed093665c4d96153fac062b4412a2044b0ea229164a505cc701" ;;
  production-planning) TASK_IDENTITY="2e84c2b95fac213e9a49cfc00fa23253732a550d4deba5aa6d8ba4d459aaf069" ;;
  wdm-design) TASK_IDENTITY="90cdc72b1a2239d90bf0827a2f30d730ffdacfd63496dc864353c636929228ae" ;;
  *) echo "unknown frozen task: $TASK_ID" >&2; exit 80 ;;
esac

if [[ ! "$CONDITION" =~ ^[ABCD]$ || ! "$POSITION" =~ ^[1-4]$ ]]; then
  echo "invalid frozen task-condition metadata" >&2
  exit 81
fi

if [[ -n "$EXPECTED_IMAGE_DIGEST" ]]; then
  if [[ ! "$EXPECTED_IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    echo "invalid expected runtime image digest" >&2
    exit 82
  fi
  printf '%s\n' "$EXPECTED_IMAGE_DIGEST" > "$IMAGE_LEDGER"
else
  rm -f "$IMAGE_LEDGER"
fi

echo "RUN_START task=$TASK_ID order=$TASK_ORDER condition=$CONDITION position=$POSITION run_id=$RUN_ID"

git fetch --quiet origin main
MAIN_MANIFEST_HASH="$(git show origin/main:manifests/experiment_manifest.final.json | sha256sum | awk '{print $1}')"
MAIN_ENV_HASH="$(git show origin/main:reproducibility/TASK_ENVIRONMENT_IDENTITIES.json | sha256sum | awk '{print $1}')"
if [[ "$MAIN_MANIFEST_HASH" != "88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a" || "$MAIN_ENV_HASH" != "26566fea65da18291160d2f45598942182d4edf23e1b95485734bc196a67945e" ]]; then
  python benchmark_execution/stopped_record.py --task "$TASK_ID" --task-order "$TASK_ORDER" --condition "$CONDITION" --condition-position "$POSITION" --run-id "$RUN_ID" --failure-class "INFRASTRUCTURE_INVALID_EXPERIMENT" --phase "PRE_PROVIDER_PREFLIGHT" --message "SCIENTIFIC_STATE_CONFLICT" --output-dir "$EVIDENCE_DIR"
  exit 83
fi

set +e
python benchmark_execution/preflight.py \
  --repo-root "$ROOT" --tb-root "$TB_ROOT" --task "$TASK_ID" --condition "$CONDITION" \
  --task-order "$TASK_ORDER" --condition-position "$POSITION" --run-id "$RUN_ID" --output "$PREFLIGHT" \
  >"$RUN_ROOT/preflight.stdout.log" 2>"$RUN_ROOT/preflight.stderr.log"
PREFLIGHT_RC=$?
set -e
if [[ $PREFLIGHT_RC -ne 0 ]]; then
  MSG="$(tail -c 1800 "$RUN_ROOT/preflight.stderr.log" || true)"
  python benchmark_execution/stopped_record.py --task "$TASK_ID" --task-order "$TASK_ORDER" --condition "$CONDITION" --condition-position "$POSITION" --run-id "$RUN_ID" --failure-class "INFRASTRUCTURE_INVALID_EXPERIMENT" --phase "PRE_PROVIDER_PREFLIGHT" --message "$MSG" --output-dir "$EVIDENCE_DIR"
  cp -f "$RUN_ROOT"/preflight.*.log "$EVIDENCE_DIR/" 2>/dev/null || true
  exit 84
fi

export FROZEN_MANIFEST_SHA256="88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a"
export FROZEN_ENV_PACKET_SHA256="26566fea65da18291160d2f45598942182d4edf23e1b95485734bc196a67945e"
export FROZEN_STATIC_ENV_PREFLIGHT="PASS"
export FROZEN_TASK_ID="$TASK_ID"
export FROZEN_TASK_IDENTITY_SHA256="$TASK_IDENTITY"
export FROZEN_CONDITION="$CONDITION"
export FROZEN_RUN_ID="$RUN_ID"
export FROZEN_TASK_ORDER="$TASK_ORDER"
export FROZEN_CONDITION_POSITION="$POSITION"
export FROZEN_RUNTIME_IMAGE_LEDGER="$IMAGE_LEDGER"
export FROZEN_MINI_ARCHIVE="$ROOT/frozen-mini.tar.gz"
export FROZEN_RUNNER_SCRIPT="$ROOT/benchmark_execution/frozen_runner.py"
export FROZEN_PROVIDER_CONSTRAINTS="$ROOT/frozen-build/provider-constraints.txt"
export FROZEN_EXECUTION_HARNESS_SHA="$GITHUB_SHA"

rm -rf "$JOBS_DIR"
set +e
harbor run \
  --path "$TB_ROOT/tasks/$TASK_ID" \
  --agent benchmark_execution.frozen_harbor_agent:FrozenMiniSweAgent \
  --model z-ai/glm-5.3-free \
  --jobs-dir "$JOBS_DIR" \
  --job-name "frozen-v0-${TASK_ORDER}-${TASK_ID}-${CONDITION}-${RUN_ID}" \
  --n-attempts 1 --n-concurrent 1 --max-retries 0 \
  --no-force-build --delete --yes \
  >"$RUN_ROOT/harbor.stdout.log" 2>"$RUN_ROOT/harbor.stderr.log"
HARBOR_RC=$?
set -e
echo "$HARBOR_RC" > "$RUN_ROOT/harbor.exitcode"

set +e
python benchmark_execution/postprocess_resume.py \
  --jobs-dir "$JOBS_DIR" --preflight "$PREFLIGHT" --task "$TASK_ID" --task-order "$TASK_ORDER" \
  --condition "$CONDITION" --condition-position "$POSITION" --run-id "$RUN_ID" --output-dir "$EVIDENCE_DIR" \
  --runtime-image-ledger "$IMAGE_LEDGER" \
  >"$RUN_ROOT/postprocess.stdout.log" 2>"$RUN_ROOT/postprocess.stderr.log"
POST_RC=$?
set -e

cp -f "$RUN_ROOT/harbor.stdout.log" "$RUN_ROOT/harbor.stderr.log" "$RUN_ROOT/harbor.exitcode" "$EVIDENCE_DIR/" 2>/dev/null || true
cp -f "$RUN_ROOT/postprocess.stdout.log" "$RUN_ROOT/postprocess.stderr.log" "$EVIDENCE_DIR/" 2>/dev/null || true

if [[ $POST_RC -ne 0 ]]; then
  MSG="$(tail -c 1800 "$RUN_ROOT/postprocess.stderr.log" || true)"
  rm -rf "$EVIDENCE_DIR"
  python benchmark_execution/stopped_record.py --task "$TASK_ID" --task-order "$TASK_ORDER" --condition "$CONDITION" --condition-position "$POSITION" --run-id "$RUN_ID" --failure-class "INFRASTRUCTURE_INVALID_EXPERIMENT" --phase "POST_PROVIDER_EVIDENCE_NORMALIZATION" --message "$MSG" --output-dir "$EVIDENCE_DIR"
  cp -R "$JOBS_DIR" "$EVIDENCE_DIR/raw-harbor-jobs" 2>/dev/null || true
  cp -f "$RUN_ROOT"/*.log "$RUN_ROOT/harbor.exitcode" "$EVIDENCE_DIR/" 2>/dev/null || true
  exit 85
fi

FAILURE_CLASS="$(python - "$EVIDENCE_DIR/run_result.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1])).get('failure_class') or '')
PY
)"
python - "$FAILURE_CLASS" <<'PY'
import sys
from benchmark_execution.resume_control import must_stop_after_condition
raise SystemExit(1 if must_stop_after_condition(sys.argv[1]) else 0)
PY
CONTROL_RC=$?
if [[ $CONTROL_RC -ne 0 ]]; then
  echo "fatal frozen execution defect at $TASK_ID/$CONDITION class=$FAILURE_CLASS" >&2
  exit 86
fi

if [[ ! -s "$IMAGE_LEDGER" ]]; then
  echo "runtime image ledger missing after condition" >&2
  exit 87
fi

echo "RUN_CHECKPOINTED task=$TASK_ID condition=$CONDITION harbor_rc=$HARBOR_RC failure_class=${FAILURE_CLASS:-NONE}"
echo "RUNTIME_IMAGE_DIGEST=$(cat "$IMAGE_LEDGER")"
