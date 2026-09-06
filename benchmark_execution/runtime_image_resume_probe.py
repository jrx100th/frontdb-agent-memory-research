from __future__ import annotations

import json
import os

from benchmark_execution.frozen_harbor_agent import FrozenMiniSweAgent


class PreservedRuntimeImageProbe(FrozenMiniSweAgent):
    """Provider-free install-only probe for the frozen same-image requirement."""

    async def install(self, environment) -> None:
        await super().install(environment)
        actual = await self._runtime_image_id(environment)
        expected = os.environ.get("FROZEN_EXPECTED_RUNTIME_IMAGE_ID", "")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        marker = {
            "actual_runtime_image_id": actual,
            "expected_runtime_image_id": expected,
            "match": bool(expected) and actual == expected,
            "benchmark_agent_runs": 0,
            "provider_calls": 0,
            "scientific_results_observed": 0,
        }
        (self.logs_dir / "provider_free_runtime_image_probe.json").write_text(
            json.dumps(marker, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(f"PROVIDER_FREE_RUNTIME_IMAGE_ACTUAL={actual}")
        print(f"PROVIDER_FREE_RUNTIME_IMAGE_EXPECTED={expected}")
        if not marker["match"]:
            raise RuntimeError(
                f"INFRASTRUCTURE_INVALID_RUNTIME_IMAGE_DRIFT expected={expected} actual={actual}"
            )
        print(f"PROVIDER_FREE_RUNTIME_IMAGE_MATCH={actual}")
        print("BENCHMARK_AGENT_RUNS=0")
        print("BENCHMARK_PROVIDER_CALLS=0")
        print("BENCHMARK_RESULTS_OBSERVED=0")
