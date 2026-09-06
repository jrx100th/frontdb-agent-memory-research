from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from benchmark_execution.frozen_harbor_agent import (
    FrozenMiniSweAgent,
    EXPECTED_ENV_PACKET_SHA256,
    EXPECTED_LITELLM_VERSION,
    EXPECTED_MINI_VERSION,
    EXPECTED_MODEL_ROUTE,
    EXPECTED_OPENAI_VERSION,
    EXPECTED_PROVIDER_BASE_SHA256,
)
from benchmark_execution.v1_identity import assert_main_runtime_identity, assert_service_references


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _task_record(manifest: dict, task_id: str) -> dict:
    matches = [x for x in manifest["tasks"] if x["task_id"] == task_id]
    if len(matches) != 1:
        raise RuntimeError(f"CONFIGURATION_INVALID_V1_TASK_IMAGE_RECORD:{task_id}:{len(matches)}")
    return matches[0]


class V1FrozenMiniSweAgent(FrozenMiniSweAgent):
    """Execution-plumbing-only bridge for v1 immutable environment materialization."""

    def _host_preflight(self, runtime_image_id: str) -> dict[str, str]:
        task_id = os.environ.get("FROZEN_TASK_ID", "")
        condition = os.environ.get("FROZEN_CONDITION", "")
        run_id = os.environ.get("FROZEN_RUN_ID", "")
        task_identity = os.environ.get("FROZEN_TASK_IDENTITY_SHA256", "")
        env_packet = os.environ.get("FROZEN_ENV_PACKET_SHA256", "")
        static_preflight = os.environ.get("FROZEN_STATIC_ENV_PREFLIGHT", "")
        provider_base = os.environ.get("TOKENROUTER_BASE_URL")
        api_key = os.environ.get("TOKENROUTER_API_KEY")
        v1_manifest_path = Path(os.environ["V1_MANIFEST_PATH"])
        v1_manifest_hash_record = Path(os.environ["V1_MANIFEST_HASH_RECORD"])
        image_manifest_path = Path(os.environ["V1_TASK_IMAGE_MANIFEST_PATH"])
        image_manifest_hash_record = Path(os.environ["V1_TASK_IMAGE_MANIFEST_HASH_RECORD"])

        if not v1_manifest_path.is_file() or not v1_manifest_hash_record.is_file():
            raise RuntimeError("CONFIGURATION_INVALID_V1_MANIFEST_MISSING")
        v1_manifest_sha = _sha(v1_manifest_path)
        if v1_manifest_hash_record.read_text(encoding="utf-8").strip() != v1_manifest_sha:
            raise RuntimeError("CONFIGURATION_INVALID_V1_MANIFEST_HASH")
        if os.environ.get("FROZEN_MANIFEST_SHA256") != v1_manifest_sha:
            raise RuntimeError("MANIFEST_IDENTITY_FAILURE")
        v1_manifest = json.loads(v1_manifest_path.read_text(encoding="utf-8"))
        if v1_manifest.get("experiment_version") != "v1-environment-materialized-1":
            raise RuntimeError("CONFIGURATION_INVALID_V1_EXPERIMENT_VERSION")
        if v1_manifest.get("v1_pre_provider_acceptance", {}).get("status") != "PASS":
            raise RuntimeError("CONFIGURATION_INVALID_V1_ACCEPTANCE_NOT_PASS")

        if env_packet != EXPECTED_ENV_PACKET_SHA256 or static_preflight != "PASS":
            raise RuntimeError("INFRASTRUCTURE_INVALID_ENVIRONMENT_PREFLIGHT")
        if condition not in {"A", "B", "C", "D"} or not task_id or not run_id or not task_identity:
            raise RuntimeError("CONFIGURATION_INVALID_RUN_METADATA")
        if not provider_base or hashlib.sha256(provider_base.encode("utf-8")).hexdigest() != EXPECTED_PROVIDER_BASE_SHA256:
            raise RuntimeError("CONFIGURATION_INVALID_PROVIDER_BASE")
        if not api_key:
            raise RuntimeError("CONFIGURATION_INVALID_PROVIDER_KEY_MISSING")
        if self.model_name != EXPECTED_MODEL_ROUTE:
            raise RuntimeError("CONFIGURATION_INVALID_MODEL_ROUTE")

        if not image_manifest_path.is_file() or not image_manifest_hash_record.is_file():
            raise RuntimeError("CONFIGURATION_INVALID_V1_IMAGE_MANIFEST_MISSING")
        image_manifest_sha = _sha(image_manifest_path)
        if image_manifest_hash_record.read_text(encoding="utf-8").strip() != image_manifest_sha:
            raise RuntimeError("CONFIGURATION_INVALID_V1_IMAGE_MANIFEST_HASH")
        if v1_manifest["execution"]["environment_materialization"]["task_environment_bundle_manifest_sha256"] != image_manifest_sha:
            raise RuntimeError("CONFIGURATION_INVALID_V1_IMAGE_MANIFEST_NOT_BOUND_TO_EXPERIMENT")
        image_manifest = json.loads(image_manifest_path.read_text(encoding="utf-8"))
        record = _task_record(image_manifest, task_id)
        if record["task_environment_source_identity_sha256"] != task_identity:
            raise RuntimeError("INFRASTRUCTURE_INVALID_TASK_SOURCE_IDENTITY")
        expected_main_id = assert_main_runtime_identity(record, runtime_image_id)
        runtime_service_refs = json.loads(os.environ.get("V1_RUNTIME_SERVICE_REFS_JSON", "{}"))
        assert_service_references(record, runtime_service_refs)
        if os.environ.get("V1_TASK_ENVIRONMENT_BUNDLE_SHA256") != record["task_environment_bundle_sha256"]:
            raise RuntimeError("INFRASTRUCTURE_INVALID_TASK_BUNDLE_IDENTITY")

        return {
            "task_id": task_id,
            "condition": condition,
            "run_id": run_id,
            "task_identity": task_identity,
            "runtime_image_id": runtime_image_id,
            "expected_runtime_image_id": expected_main_id,
            "provider_base": provider_base,
            "api_key": api_key,
            "v1_manifest_sha256": v1_manifest_sha,
            "task_environment_bundle_sha256": record["task_environment_bundle_sha256"],
        }

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        runtime_image_id = await self._runtime_image_id(environment)
        meta = self._host_preflight(runtime_image_id)

        self.logs_dir.mkdir(parents=True, exist_ok=True)
        instruction_path = self.logs_dir / "instruction.txt"
        instruction_path.write_text(instruction, encoding="utf-8")

        env = {
            "MSWEA_CONFIGURED": "true",
            "MSWEA_COST_TRACKING": "ignore_errors",
            "OPENAI_API_KEY": meta["api_key"],
            "TOKENROUTER_API_KEY": meta["api_key"],
            "TOKENROUTER_BASE_URL": meta["provider_base"],
            "FROZEN_MANIFEST_SHA256": meta["v1_manifest_sha256"],
            "FROZEN_ENV_PACKET_SHA256": EXPECTED_ENV_PACKET_SHA256,
            "FROZEN_STATIC_ENV_PREFLIGHT": "PASS",
            "FROZEN_TASK_ID": meta["task_id"],
            "FROZEN_CONDITION": meta["condition"],
            "FROZEN_RUN_ID": meta["run_id"],
            "FROZEN_TASK_IDENTITY_SHA256": meta["task_identity"],
            "FROZEN_RUNTIME_IMAGE_ID": meta["runtime_image_id"],
            "FROZEN_RUNTIME_IMAGE_EXPECTED_ID": meta["expected_runtime_image_id"],
            "FROZEN_MODEL_ROUTE": EXPECTED_MODEL_ROUTE,
            "FROZEN_CONDITION_POSITION": os.environ.get("FROZEN_CONDITION_POSITION", ""),
            "FROZEN_TASK_ORDER": os.environ.get("FROZEN_TASK_ORDER", ""),
            "FROZEN_CONFIRMATION_POLICY": "BLANK_ACCEPT_ALL_CONFIRM_MODE",
            "V1_TASK_ENVIRONMENT_BUNDLE_SHA256": meta["task_environment_bundle_sha256"],
        }

        result = await self.exec_as_agent(
            environment,
            command='"$HOME/.frozen-mswe/bin/python" /tmp/frozen_runner.py /logs/agent/instruction.txt',
            env=env,
        )

        measurement_result = await environment.exec(command="cat /logs/agent/measurement.json")
        if measurement_result.return_code != 0 or not measurement_result.stdout:
            raise RuntimeError("MEASUREMENT_EVIDENCE_MISSING")
        measurement = json.loads(measurement_result.stdout)
        accounting = measurement.get("provider_accounting") or {}
        if accounting.get("input_tokens") is not None:
            context.n_input_tokens = int(accounting["input_tokens"])
        if accounting.get("cached_tokens") is not None:
            context.n_cache_tokens = int(accounting["cached_tokens"])
        if accounting.get("output_tokens") is not None:
            context.n_output_tokens = int(accounting["output_tokens"])
        context.metadata = {
            "frozen_manifest_sha256": meta["v1_manifest_sha256"],
            "task_id": meta["task_id"],
            "condition": meta["condition"],
            "run_id": meta["run_id"],
            "runtime_image_digest": runtime_image_id,
            "task_environment_bundle_sha256": meta["task_environment_bundle_sha256"],
            "provider_preflight_calls": measurement.get("provider_preflight_calls"),
            "runner_return_code": result.return_code,
            "mini_swe_agent_version": EXPECTED_MINI_VERSION,
            "litellm_version": EXPECTED_LITELLM_VERSION,
            "openai_python_version": EXPECTED_OPENAI_VERSION,
        }
