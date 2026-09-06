#!/usr/bin/env bash
set -euo pipefail

TASK_ID="$1"
TASK_ORDER="$2"
CONDITION="$3"
POSITION="$4"
EXPECTED_IMAGE_DIGEST="${5:-}"

./benchmark_execution/run_condition.sh "$TASK_ID" "$TASK_ORDER" "$CONDITION" "$POSITION" "$EXPECTED_IMAGE_DIGEST"

RUN_ID="${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${TASK_ORDER}-${CONDITION}"
EVIDENCE_DIR="checkpoints/${TASK_ORDER}-${TASK_ID}/${CONDITION}/${RUN_ID}/evidence"
RESULT="$EVIDENCE_DIR/run_result.json"
MARKER="$EVIDENCE_DIR/condition_complete.json"
IMAGE_LEDGER="runtime-image-${TASK_ORDER}-${TASK_ID}.txt"

test -s "$RESULT"
test -s "$IMAGE_LEDGER"

python - "$RESULT" "$MARKER" <<'PY'
import json,sys
from pathlib import Path
from benchmark_execution.completion_marker import build_completion_record
result=json.load(open(sys.argv[1], encoding='utf-8'))
marker=build_completion_record(result)
Path(sys.argv[2]).write_text(json.dumps(marker, sort_keys=True, separators=(',',':'))+'\n', encoding='utf-8')
print(f"CONDITION_COMPLETE task={marker['task_id']} condition={marker['condition']} failure_class={marker.get('failure_class')}")
PY

IMAGE_DIGEST="$(cat "$IMAGE_LEDGER")"
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  printf 'image_digest=%s\n' "$IMAGE_DIGEST" >> "$GITHUB_OUTPUT"
  printf 'condition_complete_marker=%s\n' "$MARKER" >> "$GITHUB_OUTPUT"
fi
printf 'CHECKPOINT_IMAGE_DIGEST=%s\n' "$IMAGE_DIGEST"
