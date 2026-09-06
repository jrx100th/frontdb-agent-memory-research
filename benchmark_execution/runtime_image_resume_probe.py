from __future__ import annotations

import os

from benchmark_execution.frozen_harbor_agent import FrozenMiniSweAgent


class PreservedRuntimeImageProbe(FrozenMiniSweAgent):
    """Provider-free install-only probe for the frozen same-image requirement."""

    async def install(self, environment) -> None:
        await super().install(environment)
        actual = await self._runtime_image_id(environment)
        expected = os.environ.get("FROZEN_EXPECTED_RUNTIME_IMAGE_ID", "")
        if not expected or actual != expected:
            raise RuntimeError(
                f"INFRASTRUCTURE_INVALID_RUNTIME_IMAGE_DRIFT expected={expected} actual={actual}"
            )
        print(f"PROVIDER_FREE_RUNTIME_IMAGE_MATCH={actual}")
        print("BENCHMARK_AGENT_RUNS=0")
        print("BENCHMARK_PROVIDER_CALLS=0")
        print("BENCHMARK_RESULTS_OBSERVED=0")
