from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from minisweagent.agents import get_agent
from minisweagent.agents.interactive import InteractiveAgentConfig
from minisweagent.config import get_config_from_spec

from benchmark_execution import postprocess


FIXTURE = Path(__file__).with_name("fixtures") / "harbor_v0_18_terminal_bench_atrx.json"
TASK = "atrx-vep-crispr"


class ConfirmationPolicyRegressionTest(unittest.TestCase):
    def test_provider_free_reproduces_legacy_false_confirm_preflight(self):
        config = get_config_from_spec("mini")
        self.assertEqual(config["agent"].get("mode"), "confirm")
        self.assertNotIn("confirm_exit", config["agent"])
        legacy_raw_check_accepts = (
            config["agent"].get("mode") == "confirm"
            and config["agent"].get("confirm_exit") is True
        )
        self.assertIs(legacy_raw_check_accepts, False)

    def test_frozen_effective_default_is_confirm_exit_true(self):
        config = get_config_from_spec("mini")
        effective = InteractiveAgentConfig(**config["agent"])
        self.assertEqual(effective.mode, "confirm")
        self.assertIs(effective.confirm_exit, True)

    def test_same_get_agent_semantics_resolve_effective_confirmation_policy(self):
        config = get_config_from_spec("mini")
        agent = get_agent(object(), object(), config["agent"], default_type="interactive")
        self.assertEqual(agent.config.mode, "confirm")
        self.assertIs(agent.config.confirm_exit, True)


class HarborTaskNameRegressionTest(unittest.TestCase):
    def _write(self, root: Path, rel: str, obj: dict) -> Path:
        path = root / rel / "result.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj), encoding="utf-8")
        return path

    def test_accepts_bare_frozen_task_name(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            expected = self._write(root, "trial", {"task_name": TASK, "trial_name": "bare__fixture"})
            actual, obj = postprocess.find_trial_result(root, TASK)
            self.assertEqual(actual, expected)
            self.assertEqual(obj["task_name"], TASK)

    def test_accepts_harbor_v0_18_terminal_bench_namespace_fixture(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
            expected = self._write(root, "trial", fixture)
            actual, obj = postprocess.find_trial_result(root, TASK)
            self.assertEqual(actual, expected)
            self.assertEqual(obj["task_name"], f"terminal-bench/{TASK}")

    def test_rejects_unrelated_namespace_even_with_same_final_component(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, "other", {"task_name": f"some-other-task/{TASK}", "trial_name": "other__fixture"})
            with self.assertRaisesRegex(RuntimeError, r"EXPECTED_ONE_TRIAL_RESULT_FOUND_0"):
                postprocess.find_trial_result(root, TASK)

    def test_rejects_wrong_task(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            self._write(root, "wrong", {"task_name": "wrong-task", "trial_name": "wrong__fixture"})
            with self.assertRaisesRegex(RuntimeError, r"EXPECTED_ONE_TRIAL_RESULT_FOUND_0"):
                postprocess.find_trial_result(root, TASK)

    def test_selects_exact_terminal_bench_task_while_rejecting_unrelated_same_leaf(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
            expected = self._write(root, "target", fixture)
            self._write(root, "other", {"task_name": f"some-other-task/{TASK}", "trial_name": "other__fixture"})
            self._write(root, "wrong", {"task_name": "wrong-task", "trial_name": "wrong__fixture"})
            actual, obj = postprocess.find_trial_result(root, TASK)
            self.assertEqual(actual, expected)
            self.assertEqual(obj["trial_name"], fixture["trial_name"])


if __name__ == "__main__":
    unittest.main()
