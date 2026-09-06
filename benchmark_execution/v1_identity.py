from __future__ import annotations

import json
from pathlib import Path
import re

IMAGE_ID_RE = re.compile(r"sha256:[0-9a-f]{64}")


def load_task_record(manifest_path: Path, task_id: str) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    matches = [x for x in manifest["tasks"] if x["task_id"] == task_id]
    if len(matches) != 1:
        raise RuntimeError(f"V1_RUNTIME_IDENTITY_TASK_UNRESOLVED:{task_id}:{len(matches)}")
    return matches[0]


def expected_main_runtime_image_id(task_record: dict) -> str:
    main = (task_record.get("built_services") or {}).get("main") or {}
    value = str(main.get("runtime_image_id_at_materialization") or "")
    if not IMAGE_ID_RE.fullmatch(value):
        raise RuntimeError("V1_RUNTIME_IDENTITY_EXPECTED_MAIN_ID_INVALID")
    return value


def assert_main_runtime_identity(task_record: dict, actual_image_id: str) -> str:
    expected = expected_main_runtime_image_id(task_record)
    if not IMAGE_ID_RE.fullmatch(str(actual_image_id)):
        raise RuntimeError("INFRASTRUCTURE_INVALID_RUNTIME_IMAGE_ID_MALFORMED")
    if actual_image_id != expected:
        raise RuntimeError(
            f"INFRASTRUCTURE_INVALID_RUNTIME_IMAGE_DRIFT expected={expected} actual={actual_image_id}"
        )
    return expected


def assert_service_references(task_record: dict, actual_service_refs: dict[str, str]) -> None:
    expected = task_record.get("service_identity") or {}
    if actual_service_refs != expected:
        raise RuntimeError(
            "INFRASTRUCTURE_INVALID_RUNTIME_SERVICE_IDENTITY_DRIFT "
            f"expected={json.dumps(expected, sort_keys=True)} actual={json.dumps(actual_service_refs, sort_keys=True)}"
        )
    if any("@sha256:" not in ref for ref in actual_service_refs.values()):
        raise RuntimeError("INFRASTRUCTURE_INVALID_MUTABLE_RUNTIME_SERVICE_REFERENCE")
