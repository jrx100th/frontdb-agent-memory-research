from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

from harbor.agents.installed.mini_swe_agent import MiniSweAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


EXPECTED_MANIFEST_SHA256 = "88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a"
EXPECTED_PROVIDER_BASE_SHA256 = "f76d53a0e94e3837023542b48c5b2226b21c3ad37cae446272a2743b7579ee5d"
EXPECTED_ENV_PACKET_SHA256 = "26566fea65da18291160d2f45598942182d4edf23e1b95485734bc196a67945e"
EXPECTED_MODEL_ROUTE = "z-ai/glm-5.3-free"
EXPECTED_MINI_VERSION = "2.4.6"
EXPECTED_LITELLM_VERSION = "1.99.0"


class FrozenMiniSweAgent(MiniSweAgent):
    """Execution bridge only; scientific code comes from the frozen patched archive."""

    def __init__(self, *args, **kwargs):
        kwargs["version"] = EXPECTED_MINI_VERSION
        super().__init__(*args, **kwargs)

    @staticmethod
    def name() -> str:
        return "mini-swe-agent"

    async def install(self, environment: BaseEnvironment) -> None:
        archive = Path(os.environ["FROZEN_MINI_ARCHIVE"])
        runner = Path(os.environ["FROZEN_RUNNER_SCRIPT"])
        constraints = Path(os.environ["FROZEN_PROVIDER_CONSTRAINTS"])
        if not archive.is_file() or not runner.is_file() or not constraints.is_file():
            raise RuntimeError("FROZEN_AGENT_INSTALL_INPUT_MISSING")

        await environment.upload_file(archive, "/tmp/frozen-mini.tar.gz")
        await environment.upload_file(runner, "/tmp/frozen_runner.py")
        await environment.upload_file(constraints, "/tmp/frozen-provider-constraints.txt")

        await self.exec_as_root(
            environment,
            command=(
                "if command -v apt-get >/dev/null 2>&1; then "
                "  apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y curl build-essential git ca-certificates; "
                "elif command -v apk >/dev/null 2>&1; then "
                "  apk add --no-cache curl bash build-base git python3 py3-pip ca-certificates; "
                "elif command -v dnf >/dev/null 2>&1; then "
                "  dnf install -y curl git gcc make ca-certificates; "
                "elif command -v yum >/dev/null 2>&1; then "
                "  yum install -y curl git gcc make ca-certificates; "
                "else echo 'FROZEN_SETUP_NO_SUPPORTED_PACKAGE_MANAGER' >&2; exit 86; fi"
            ),
        )

        await self.exec_as_agent(
            environment,
            command=(
                "set -euo pipefail; "
                "if ! command -v uv >/dev/null 2>&1; then "
                "  curl -LsSf https://astral.sh/uv/0.7.13/install.sh | sh; "
                "fi; "
                "export PATH=\"$HOME/.local/bin:$PATH\"; "
                "rm -rf \"$HOME/frozen-mini-src\" \"$HOME/.frozen-mswe\"; "
                "mkdir -p \"$HOME/frozen-mini-src\"; "
                "tar -xzf /tmp/frozen-mini.tar.gz -C \"$HOME/frozen-mini-src\" --strip-components=1; "
                "uv venv --python 3.11 \"$HOME/.frozen-mswe\"; "
                "uv pip install --python \"$HOME/.frozen-mswe/bin/python\" "
                "  --constraint /tmp/frozen-provider-constraints.txt \"$HOME/frozen-mini-src[full]\"; "
                "\"$HOME/.frozen-mswe/bin/python\" - <<'PY'\n"
                "import importlib.metadata as md\n"
                "import litellm\n"
                "assert md.version('mini-swe-agent') == '2.4.6'\n"
                "assert md.version('litellm') == '1.99.0'\n"
                "print('FROZEN_AGENT_INSTALL_VERIFIED')\n"
                "PY"
            ),
        )

    def _runtime_image_id(self, environment: BaseEnvironment) -> str:
        image_name = None
        env_vars = getattr(environment, "_env_vars", None)
        if env_vars is not None:
            image_name = getattr(env_vars, "main_image_name", None)
        if not image_name:
            environment_id = getattr(environment, "environment_id", None)
            if not environment_id:
                raise RuntimeError("RUNTIME_IMAGE_NAME_UNRESOLVED")
            image_name = f"hb__{environment_id}"
        try:
            value = subprocess.check_output(
                ["docker", "image", "inspect", str(image_name), "--format", "{{.Id}}"],
                text=True,
            ).strip()
        except Exception as exc:
            raise RuntimeError("RUNTIME_IMAGE_DIGEST_UNRESOLVED") from exc
        if not value.startswith("sha256:"):
            raise RuntimeError("RUNTIME_IMAGE_DIGEST_MALFORMED")
        return value

    def _host_preflight(self, runtime_image_id: str) -> dict[str, str]:
        task_id = os.environ.get("FROZEN_TASK_ID", "")
        condition = os.environ.get("FROZEN_CONDITION", "")
        run_id = os.environ.get("FROZEN_RUN_ID", "")
        task_identity = os.environ.get("FROZEN_TASK_IDENTITY_SHA256", "")
        env_packet = os.environ.get("FROZEN_ENV_PACKET_SHA256", "")
        manifest_sha = os.environ.get("FROZEN_MANIFEST_SHA256", "")
        static_preflight = os.environ.get("FROZEN_STATIC_ENV_PREFLIGHT", "")
        provider_base = os.environ.get("TOKENROUTER_BASE_URL")
        api_key = os.environ.get("TOKENROUTER_API_KEY")

        if manifest_sha != EXPECTED_MANIFEST_SHA256:
            raise RuntimeError("MANIFEST_IDENTITY_FAILURE")
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

        ledger_path = Path(os.environ["FROZEN_RUNTIME_IMAGE_LEDGER"])
        if ledger_path.exists():
            expected_image_id = ledger_path.read_text(encoding="utf-8").strip()
            if expected_image_id != runtime_image_id:
                raise RuntimeError("INFRASTRUCTURE_INVALID_RUNTIME_IMAGE_DRIFT")
        else:
            ledger_path.write_text(runtime_image_id + "\n", encoding="utf-8")
            expected_image_id = runtime_image_id

        return {
            "task_id": task_id,
            "condition": condition,
            "run_id": run_id,
            "task_identity": task_identity,
            "runtime_image_id": runtime_image_id,
            "expected_runtime_image_id": expected_image_id,
            "provider_base": provider_base,
            "api_key": api_key,
        }

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        runtime_image_id = self._runtime_image_id(environment)
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
            "FROZEN_MANIFEST_SHA256": EXPECTED_MANIFEST_SHA256,
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
        }

        result = await self.exec_as_agent(
            environment,
            command='"$HOME/.frozen-mswe/bin/python" /tmp/frozen_runner.py /logs/agent/instruction.txt',
            env=env,
        )

        measurement_result = await environment.exec(
            command="cat /logs/agent/measurement.json",
        )
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
            "frozen_manifest_sha256": EXPECTED_MANIFEST_SHA256,
            "task_id": meta["task_id"],
            "condition": meta["condition"],
            "run_id": meta["run_id"],
            "runtime_image_digest": runtime_image_id,
            "provider_preflight_calls": measurement.get("provider_preflight_calls"),
            "runner_return_code": result.return_code,
        }
