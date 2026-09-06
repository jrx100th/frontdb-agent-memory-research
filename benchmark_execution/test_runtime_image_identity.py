from __future__ import annotations

import asyncio
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from benchmark_execution.frozen_harbor_agent import FrozenMiniSweAgent


class _ComposeResult:
    def __init__(self, stdout: str, return_code: int = 0):
        self.stdout = stdout
        self.return_code = return_code


class _FakeHarborEnvironment:
    environment_id = "003ee692305bb20c5a4c407be0ebf97f"
    _env_vars = SimpleNamespace(main_image_name="hb__003ee692305bb20c5a4c407be0ebf97f")

    async def _run_docker_compose_command(self, command, check=True, **kwargs):
        if command == ["ps", "-q", "main"]:
            return _ComposeResult("container-123\n")
        raise AssertionError(f"unexpected compose command: {command}")


class ProviderFreeRuntimeImageProbe(FrozenMiniSweAgent):
    """Install-only Harbor probe. It cannot enter agent.run/provider execution."""

    async def install(self, environment) -> None:
        await super().install(environment)
        immutable_image_id = await self._runtime_image_id(environment)
        print(f"PROVIDER_FREE_RUNTIME_IMAGE_ID={immutable_image_id}")
        print("BENCHMARK_AGENT_RUNS=0")
        print("BENCHMARK_PROVIDER_CALLS=0")
        print("BENCHMARK_RESULTS_OBSERVED=0")


class RuntimeImageIdentityRegressionTest(unittest.TestCase):
    def test_resolves_immutable_image_id_from_running_main_container(self):
        env = _FakeHarborEnvironment()
        agent = object.__new__(FrozenMiniSweAgent)
        immutable_image_id = "sha256:" + "a" * 64

        def fake_check_output(argv, text=True):
            if argv[:3] == ["docker", "image", "inspect"]:
                raise subprocess.CalledProcessError(1, argv)
            if argv[:2] == ["docker", "inspect"] and argv[2] == "container-123":
                self.assertEqual(argv[-2:], ["--format", "{{.Image}}"])
                return immutable_image_id + "\n"
            raise AssertionError(f"unexpected docker command: {argv}")

        with patch("benchmark_execution.frozen_harbor_agent.subprocess.check_output", side_effect=fake_check_output):
            resolved = asyncio.run(agent._runtime_image_id(env))

        self.assertEqual(resolved, immutable_image_id)


if __name__ == "__main__":
    unittest.main()
