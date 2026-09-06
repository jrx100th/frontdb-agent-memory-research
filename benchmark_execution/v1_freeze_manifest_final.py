from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from benchmark_execution import v1_freeze_manifest as base

INTERNAL_IMAGE_PACKET_LABEL = "v1-environment-materialized"
FINAL_EXPERIMENT_VERSION = "v1-environment-materialized-1"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v0-manifest", type=Path, required=True)
    ap.add_argument("--image-manifest", type=Path, required=True)
    ap.add_argument("--image-manifest-hash", type=Path, required=True)
    ap.add_argument("--gates-evidence", type=Path, required=True)
    ap.add_argument("--memory-evidence", type=Path, required=True)
    ap.add_argument("--v0-replay-evidence", type=Path, required=True)
    ap.add_argument("--freeze-parent", required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--hash-output", type=Path, required=True)
    args = ap.parse_args()

    images = json.loads(args.image_manifest.read_text(encoding="utf-8"))
    if images.get("experiment_version") != INTERNAL_IMAGE_PACKET_LABEL:
        raise RuntimeError(
            f"V1_IMAGE_PACKET_INTERNAL_LABEL_CHANGED:{images.get('experiment_version')}"
        )

    forwarded = [
        "v1_freeze_manifest.py",
        "--v0-manifest", str(args.v0_manifest),
        "--image-manifest", str(args.image_manifest),
        "--image-manifest-hash", str(args.image_manifest_hash),
        "--gates-evidence", str(args.gates_evidence),
        "--memory-evidence", str(args.memory_evidence),
        "--v0-replay-evidence", str(args.v0_replay_evidence),
        "--freeze-parent", args.freeze_parent,
        "--output", str(args.output),
        "--hash-output", str(args.hash_output),
    ]
    old_argv = sys.argv
    try:
        sys.argv = forwarded
        rc = base.main()
    finally:
        sys.argv = old_argv
    if rc != 0:
        raise RuntimeError(f"V1_BASE_FREEZE_FAILED:{rc}")

    v1 = json.loads(args.output.read_text(encoding="utf-8"))
    if v1.get("experiment_version") != FINAL_EXPERIMENT_VERSION:
        raise RuntimeError(f"V1_FINAL_EXPERIMENT_VERSION_INVALID:{v1.get('experiment_version')}")

    em = v1["execution"]["environment_materialization"]
    em["environment_packet_internal_experiment_label"] = INTERNAL_IMAGE_PACKET_LABEL
    em["final_experiment_version"] = FINAL_EXPERIMENT_VERSION
    em["version_label_distinction"] = {
        "environment_materialization_packet_label": INTERNAL_IMAGE_PACKET_LABEL,
        "final_experiment_manifest_version": FINAL_EXPERIMENT_VERSION,
        "image_manifest_rewritten_for_version_label": False,
        "meaning": "The frozen image manifest retains its internal materialization-stage label; the final experiment version is a separate v1 experiment identifier.",
    }

    v0 = json.loads(args.v0_manifest.read_text(encoding="utf-8"))
    base.assert_science_equal(v0, v1)
    payload = base.canon(v1)
    args.output.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    args.hash_output.write_text(digest + "\n", encoding="utf-8")

    print("V1_IMAGE_PACKET_INTERNAL_LABEL=" + INTERNAL_IMAGE_PACKET_LABEL)
    print("V1_FINAL_EXPERIMENT_VERSION=" + FINAL_EXPERIMENT_VERSION)
    print("V1_IMAGE_MANIFEST_REWRITTEN_FOR_VERSION_LABEL=NO")
    print("V1_SCIENTIFIC_DIFFERENCES_FROM_V0=NONE")
    print("V1_MANIFEST_SHA256=" + digest)
    print("PROVIDER_CALLS_DURING_V1_PREPARATION=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
