from __future__ import annotations

import json
import os
from pathlib import Path

from benchmark_execution.v1_harbor_agent import V1FrozenMiniSweAgent


class V1EvidenceFrozenMiniSweAgent(V1FrozenMiniSweAgent):
    """Persist successful immutable-image preflight before entering model execution."""

    def _host_preflight(self, runtime_image_id: str) -> dict[str, str]:
        meta = super()._host_preflight(runtime_image_id)
        path_value = os.environ.get("V1_RUNTIME_IDENTITY_EVIDENCE", "")
        if not path_value:
            raise RuntimeError("CONFIGURATION_INVALID_V1_RUNTIME_IDENTITY_EVIDENCE_PATH")
        path = Path(path_value)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "schema_version": 1,
            "status": "PASS",
            "task_id": meta["task_id"],
            "condition": meta["condition"],
            "run_id": meta["run_id"],
            "actual_main_runtime_image_id": runtime_image_id,
            "expected_main_runtime_image_id": meta["expected_runtime_image_id"],
            "task_environment_bundle_sha256": meta["task_environment_bundle_sha256"],
            "manifest_sha256": meta["v1_manifest_sha256"],
            "provider_calls_before_identity_acceptance": 0,
        }
        path.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        return meta
