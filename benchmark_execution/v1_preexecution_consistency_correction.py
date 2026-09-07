from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess

from benchmark_execution.v1_generate_execution_workflow import build_workflow

SUPERSEDED_SHA256 = "0a7fc0f7852d2ac3e6f4a117317e86f494760a4bf424b992bd8d2c587423493a"
V1_VERSION = "v1-environment-materialized-1"
CANONICAL_IMAGE_MANIFEST_SHA256 = "2b2e05f1e6434e67767d6fe42b51e353a56ad5f275a320fe81f79a9fa9ca6d96"
ACCEPTED_G3_G10_COMMIT = "2137004e365344a6e2572f07a5c6dc065eeaac73"
V0_MANIFEST_SHA256 = "88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a"
EXPECTED_OUTPUT_ROOT = "results/v1/{task_order:02d}-{task_id}/{condition}/{run_id}/"
EXPECTED_HASH_RECORD = "reproducibility/V1_MANIFEST_SHA256.txt"
ALLOWED_MANIFEST_PATHS = {
    ("execution", "output_root_template"),
    ("hash_record_path",),
}


def canon(obj: object) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def remove_allowed(obj: dict) -> dict:
    out = copy.deepcopy(obj)
    for path in ALLOWED_MANIFEST_PATHS:
        cur = out
        for key in path[:-1]:
            cur = cur[key]
        cur.pop(path[-1], None)
    return out


def require_contains(path: Path, *needles: str) -> str:
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            raise RuntimeError(f"V1_BINDING_AUDIT_MISSING:{path}:{needle}")
    if SUPERSEDED_SHA256 in text:
        raise RuntimeError(f"V1_BINDING_AUDIT_SUPERSEDED_SHA_HARDCODED:{path}")
    return text


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "manifests/experiment_manifest.v1.final.json"
    hash_record = root / "reproducibility/V1_MANIFEST_SHA256.txt"
    images_path = root / "reproducibility/v1_task_images.json"
    image_hash_record = root / "reproducibility/V1_TASK_IMAGE_MANIFEST_SHA256.txt"
    provenance_dir = root / "reproducibility/v1_manifest_provenance"
    audit_dir = root / "reproducibility/v1_preexecution_consistency"

    old_bytes = manifest_path.read_bytes()
    old_sha = sha_bytes(old_bytes)
    if old_sha != SUPERSEDED_SHA256:
        raise RuntimeError(f"V1_SUPERSEDED_MANIFEST_IDENTITY_UNEXPECTED:{old_sha}")
    if hash_record.read_text(encoding="utf-8").strip() != SUPERSEDED_SHA256:
        raise RuntimeError("V1_SUPERSEDED_HASH_RECORD_MISMATCH")

    old = json.loads(old_bytes)
    if old.get("experiment_version") != V1_VERSION:
        raise RuntimeError("V1_VERSION_CHANGED_BEFORE_CORRECTION")
    if old["execution"].get("output_root_template") != "results/v0/{task_order:02d}-{task_id}/{condition}/{run_id}/":
        raise RuntimeError("V1_EXPECTED_STALE_OUTPUT_ROOT_NOT_FOUND")
    if old.get("hash_record_path") != "reproducibility/FINAL_MANIFEST_SHA256.txt":
        raise RuntimeError("V1_EXPECTED_STALE_HASH_RECORD_PATH_NOT_FOUND")

    if sha_file(images_path) != CANONICAL_IMAGE_MANIFEST_SHA256:
        raise RuntimeError("V1_CANONICAL_IMAGE_MANIFEST_CHANGED")
    if image_hash_record.read_text(encoding="utf-8").strip() != CANONICAL_IMAGE_MANIFEST_SHA256:
        raise RuntimeError("V1_CANONICAL_IMAGE_HASH_RECORD_CHANGED")

    provenance_dir.mkdir(parents=True, exist_ok=True)
    superseded_copy = provenance_dir / f"experiment_manifest.v1.superseded-pre-provider.{SUPERSEDED_SHA256}.json"
    superseded_copy.write_bytes(old_bytes)
    if sha_file(superseded_copy) != SUPERSEDED_SHA256:
        raise RuntimeError("V1_SUPERSEDED_PROVENANCE_COPY_FAILURE")

    corrected = copy.deepcopy(old)
    corrected["execution"]["output_root_template"] = EXPECTED_OUTPUT_ROOT
    corrected["hash_record_path"] = EXPECTED_HASH_RECORD

    if corrected.get("experiment_version") != V1_VERSION:
        raise RuntimeError("V1_VERSION_CHANGED_DURING_CORRECTION")
    if remove_allowed(old) != remove_allowed(corrected):
        raise RuntimeError("V1_SCIENTIFIC_OR_NONAUTHORIZED_MANIFEST_CHANGE")
    if old["execution"]["schedule"] != corrected["execution"]["schedule"]:
        raise RuntimeError("V1_SCHEDULE_CHANGED")
    flattened = [
        (slot["task_order"], slot["task_id"], pos, condition)
        for slot in corrected["execution"]["schedule"]
        for pos, condition in enumerate(slot["condition_order"], 1)
    ]
    if len(flattened) != 48 or len({(x[1], x[3]) for x in flattened}) != 48:
        raise RuntimeError("V1_SCHEDULE_CARDINALITY_CHANGED")

    new_bytes = canon(corrected)
    new_sha = sha_bytes(new_bytes)
    if new_sha == SUPERSEDED_SHA256:
        raise RuntimeError("V1_CORRECTED_MANIFEST_SHA_DID_NOT_CHANGE")
    manifest_path.write_bytes(new_bytes)
    hash_record.write_text(new_sha + "\n", encoding="utf-8")

    # Provider-backed v1 identity binding audit. These paths must resolve the
    # currently recorded v1 manifest SHA at runtime; none may hardcode the
    # superseded pre-provider v1 SHA.
    preflight = require_contains(
        root / "benchmark_execution/v1_preflight.py",
        "reproducibility/V1_MANIFEST_SHA256.txt",
        "v1_sha = sha(v1_path)",
        "CONFIGURATION_INVALID_V1_MANIFEST_HASH",
    )
    runner = require_contains(
        root / "benchmark_execution/run_v1_condition_checkpointed.sh",
        'export FROZEN_MANIFEST_SHA256="$(cat reproducibility/V1_MANIFEST_SHA256.txt)"',
        'export V1_RUNNER_SHIM_SCRIPT="$ROOT/benchmark_execution/v1_runner_shim.py"',
        "postprocess_v1.py",
    )
    harbor = require_contains(
        root / "benchmark_execution/v1_harbor_agent.py",
        'os.environ.get("FROZEN_MANIFEST_SHA256") != v1_manifest_sha',
        'environment.upload_file(shim, "/tmp/v1_runner_shim.py")',
        "/tmp/v1_runner_shim.py /logs/agent/instruction.txt",
    )
    shim = require_contains(
        root / "benchmark_execution/v1_runner_shim.py",
        'expected = os.environ.get("FROZEN_MANIFEST_SHA256", "")',
        "module.EXPECTED_MANIFEST_SHA256 = expected",
        "FROZEN_SCIENTIFIC_RUNNER_MODIFIED=NO",
    )
    postprocess = require_contains(
        root / "benchmark_execution/postprocess_v1.py",
        "v1_sha = sha(args.v1_manifest)",
        "V1_POSTPROCESS_MANIFEST_HASH_INVALID",
        'result["output_path"] = f"results/v1/{args.task_order:02d}-{args.task}/{args.condition}/{args.run_id}/"',
    )
    identity = require_contains(
        root / "benchmark_execution/v1_identity.py",
        "assert_main_runtime_identity",
        "assert_service_references",
    )
    generator = require_contains(
        root / "benchmark_execution/v1_generate_execution_workflow.py",
        "workflow_dispatch:",
        "run_v1_condition_checkpointed.sh",
    )

    generated_workflow = build_workflow()
    if generated_workflow.count("Execute exactly one frozen v1 task-condition") != 48:
        raise RuntimeError("V1_GENERATED_WORKFLOW_CONDITION_COUNT_CHANGED")
    if "push:" in generated_workflow.split("jobs:", 1)[0]:
        raise RuntimeError("V1_GENERATED_WORKFLOW_AUTO_LAUNCH_FORBIDDEN")
    if SUPERSEDED_SHA256 in generated_workflow:
        raise RuntimeError("V1_GENERATED_WORKFLOW_SUPERSEDED_SHA_HARDCODED")

    # aggregate.py is the preserved v0 aggregator and is not referenced by the
    # v1 execution runner or generated workflow. Its v0 SHA binding is retained.
    aggregate = (root / "benchmark_execution/aggregate.py").read_text(encoding="utf-8")
    if f'MANIFEST_SHA = "{V0_MANIFEST_SHA256}"' not in aggregate:
        raise RuntimeError("V0_AGGREGATOR_PROVENANCE_CHANGED")
    if "benchmark_execution/aggregate.py" in generated_workflow or "aggregate.py" in runner:
        raise RuntimeError("V1_EXECUTION_INCORRECTLY_USES_V0_AGGREGATOR")

    # The frozen scientific runner remains byte-for-byte untouched relative to
    # the independently accepted G3-G10 commit. The v1 shim changes only its
    # in-memory manifest identity constant before main().
    frozen_now = (root / "benchmark_execution/frozen_runner.py").read_bytes()
    frozen_accepted = subprocess.check_output(
        ["git", "-C", str(root), "show", f"{ACCEPTED_G3_G10_COMMIT}:benchmark_execution/frozen_runner.py"]
    )
    if frozen_now != frozen_accepted:
        raise RuntimeError("V1_FROZEN_SCIENTIFIC_RUNNER_CHANGED")

    if corrected["execution"]["output_root_template"] != EXPECTED_OUTPUT_ROOT:
        raise RuntimeError("V1_OUTPUT_ROOT_CORRECTION_FAILED")
    if corrected["hash_record_path"] != EXPECTED_HASH_RECORD:
        raise RuntimeError("V1_HASH_RECORD_PATH_CORRECTION_FAILED")
    if sha_file(manifest_path) != hash_record.read_text(encoding="utf-8").strip():
        raise RuntimeError("V1_CORRECTED_MANIFEST_HASH_RECORD_MISMATCH")

    provenance = {
        "schema_version": 1,
        "status": "SUPERSEDED_PRE_PROVIDER_METADATA_CONSISTENCY_ONLY",
        "experiment_version": V1_VERSION,
        "superseded_manifest_sha256": SUPERSEDED_SHA256,
        "corrected_manifest_sha256": new_sha,
        "superseded_manifest_copy": str(superseded_copy.relative_to(root)),
        "reason": "Correct stale v0 output_root_template and hash_record_path before any v1 provider execution.",
        "authorized_manifest_changes": {
            "execution.output_root_template": EXPECTED_OUTPUT_ROOT,
            "hash_record_path": EXPECTED_HASH_RECORD,
        },
        "scientific_variable_changed": False,
        "provider_calls_during_correction": 0,
    }
    (provenance_dir / "SUPERSESSION.json").write_bytes(canon(provenance))

    audit = {
        "schema_version": 1,
        "status": "PASS",
        "superceded_spelling_alias": SUPERSEDED_SHA256,
        "superseded_v1_manifest_sha256": SUPERSEDED_SHA256,
        "corrected_v1_manifest_sha256": new_sha,
        "experiment_version": V1_VERSION,
        "output_root_template": EXPECTED_OUTPUT_ROOT,
        "hash_record_path": EXPECTED_HASH_RECORD,
        "canonical_image_manifest_sha256": CANONICAL_IMAGE_MANIFEST_SHA256,
        "manifest_hash_record_matches": True,
        "postprocess_output_root_matches_manifest": True,
        "schedule_condition_count": len(flattened),
        "schedule_unchanged": True,
        "scientific_variable_changed": False,
        "provider_calls": 0,
        "execution_path_new_sha_binding": {
            "v1_preflight": "dynamic manifest bytes + V1_MANIFEST_SHA256.txt",
            "run_v1_condition_checkpointed": "exports FROZEN_MANIFEST_SHA256 from V1_MANIFEST_SHA256.txt",
            "v1_harbor_agent": "re-hashes v1 manifest and compares runtime FROZEN_MANIFEST_SHA256 before provider access",
            "v1_runner_shim": "binds unchanged frozen_runner EXPECTED_MANIFEST_SHA256 in memory to FROZEN_MANIFEST_SHA256",
            "postprocess_v1": "re-hashes v1 manifest and compares V1_MANIFEST_SHA256.txt",
            "v1_generate_execution_workflow": "48 workflow_dispatch-only jobs route through run_v1_condition_checkpointed.sh",
            "v1_identity": "immutable task/service identity checks independent of manifest hash hardcoding",
            "aggregate.py": "preserved v0-only aggregator; not referenced by v1 execution path",
        },
        "superseded_sha_hardcoded_in_provider_backed_v1_paths": False,
        "frozen_scientific_runner_modified": False,
    }
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "CONSISTENCY_GATE.json").write_bytes(canon(audit))

    print(f"SUPERSEDED_V1_MANIFEST_SHA256={SUPERSEDED_SHA256}")
    print(f"CORRECTED_V1_MANIFEST_SHA256={new_sha}")
    print(f"V1_VERSION={V1_VERSION}")
    print(f"OUTPUT_ROOT_TEMPLATE={EXPECTED_OUTPUT_ROOT}")
    print(f"HASH_RECORD_PATH={EXPECTED_HASH_RECORD}")
    print(f"CANONICAL_IMAGE_MANIFEST_SHA256={CANONICAL_IMAGE_MANIFEST_SHA256}")
    print("EXECUTION_PATH_NEW_SHA_BINDING=PASS")
    print("SCHEDULE_UNCHANGED=YES")
    print("SCIENTIFIC_VARIABLE_CHANGED=NO")
    print("PROVIDER_CALLS_DURING_CORRECTION=0")
    print("READY_FOR_PROVIDER_EXECUTION=YES_BUT_NOT_AUTHORIZED_TO_LAUNCH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
