from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from benchmark_execution.frozen_harbor_agent import FrozenMiniSweAgent

DIGEST_RE = re.compile(r"digest:\s*(sha256:[0-9a-f]{64})")


def _require(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"V1_MATERIALIZATION_MISSING_{name}")
    return value


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


class V1ImageMaterializer(FrozenMiniSweAgent):
    """Provider-free install-only agent that publishes Harbor's exact built main image.

    It deliberately does not call FrozenMiniSweAgent.install(): materialization must
    capture the pristine Terminal-Bench runtime image before any agent installation
    mutates the running container filesystem.
    """

    async def install(self, environment) -> None:
        task_id = _require("V1_TASK_ID")
        task_order = int(_require("V1_TASK_ORDER"))
        source_identity = _require("V1_TASK_SOURCE_IDENTITY")
        repository = _require("V1_IMAGE_REPOSITORY")
        transport_tag = _require("V1_IMAGE_TRANSPORT_TAG")
        output_path = Path(_require("V1_MATERIALIZATION_OUTPUT"))

        if os.environ.get("TOKENROUTER_BASE_URL") or os.environ.get("TOKENROUTER_API_KEY"):
            raise RuntimeError("V1_MATERIALIZATION_PROVIDER_BOUNDARY_VIOLATION")

        actual_image_id = await self._runtime_image_id(environment)
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", actual_image_id):
            raise RuntimeError("V1_MATERIALIZATION_RUNTIME_IMAGE_ID_MALFORMED")

        tagged_ref = f"{repository}:{transport_tag}"
        subprocess.check_call(["docker", "tag", actual_image_id, tagged_ref])
        pushed = subprocess.check_output(["docker", "push", tagged_ref], text=True, stderr=subprocess.STDOUT)
        matches = DIGEST_RE.findall(pushed)
        if len(matches) != 1:
            raise RuntimeError(f"V1_MATERIALIZATION_PUSH_DIGEST_UNRESOLVED:{matches}")
        registry_digest = matches[0]
        immutable_ref = f"{repository}@{registry_digest}"

        raw = subprocess.check_output(["docker", "buildx", "imagetools", "inspect", immutable_ref, "--raw"])
        raw_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
        if raw_digest != registry_digest:
            raise RuntimeError(
                f"V1_MATERIALIZATION_REGISTRY_DIGEST_MISMATCH:{raw_digest}!={registry_digest}"
            )

        subprocess.check_call(["docker", "pull", immutable_ref], stdout=subprocess.DEVNULL)
        pulled_image_id = subprocess.check_output(
            ["docker", "image", "inspect", immutable_ref, "--format", "{{.Id}}"], text=True
        ).strip().lower()
        if pulled_image_id != actual_image_id:
            raise RuntimeError(
                f"V1_MATERIALIZATION_ROUNDTRIP_IMAGE_ID_MISMATCH:{pulled_image_id}!={actual_image_id}"
            )
        platform = subprocess.check_output(
            ["docker", "image", "inspect", actual_image_id, "--format", "{{.Os}}/{{.Architecture}}"], text=True
        ).strip()
        if platform != "linux/amd64":
            raise RuntimeError(f"V1_MATERIALIZATION_UNEXPECTED_PLATFORM:{platform}")

        record = {
            "schema_version": 1,
            "experiment_version": "v1-environment-materialized",
            "task_order": task_order,
            "task_id": task_id,
            "task_environment_source_identity_sha256": source_identity,
            "image_repository": repository,
            "transport_tag_non_authoritative": transport_tag,
            "registry_manifest_digest": registry_digest,
            "immutable_image_reference": immutable_ref,
            "runtime_image_id_at_materialization": actual_image_id,
            "roundtrip_runtime_image_id": pulled_image_id,
            "platform": platform,
            "provider_calls": 0,
            "identity_authority": "registry_manifest_digest_and_immutable_image_reference",
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(_canon(record), encoding="utf-8")
        print(f"V1_IMAGE_MATERIALIZED task={task_id} immutable={immutable_ref}")
        print(f"V1_RUNTIME_IMAGE_ID={actual_image_id}")
        print("BENCHMARK_AGENT_RUNS=0")
        print("BENCHMARK_PROVIDER_CALLS=0")
        print("BENCHMARK_RESULTS_OBSERVED=0")
