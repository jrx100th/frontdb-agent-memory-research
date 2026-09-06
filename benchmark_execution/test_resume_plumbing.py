from __future__ import annotations

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from benchmark_execution.postprocess_resume import MANIFEST_SHA, normalize, reconcile_attempt_ledgers
from benchmark_execution.resume_control import must_stop_after_condition


class AttemptLedgerTests(unittest.TestCase):
    def setUp(self):
        self.durable = [
            {"attempt_number": i, "accounting_status": "COUNTED", "total_tokens": i}
            for i in range(1, 57)
        ]
        self.packet = {
            "aggregate": {"accounting_status": "VALID", "attempt_count": 56, "total_provider_tokens": sum(range(1,57))},
            "attempts": self.durable,
        }

    def test_shorter_exact_prefix_accepts_durable_authority(self):
        trajectory = {"info": {"provider_attempts": copy.deepcopy(self.durable[:46])}}
        attempts, _, meta = reconcile_attempt_ledgers(None, trajectory, self.packet)
        self.assertEqual(attempts, self.durable)
        self.assertEqual(len(attempts), 56)
        self.assertEqual(meta["trajectory_attempt_count"], 46)
        self.assertEqual(meta["authoritative_source"], "provider_attempts.json")

    def test_common_prefix_divergence_fails_closed(self):
        trajectory = {"info": {"provider_attempts": copy.deepcopy(self.durable[:46])}}
        trajectory["info"]["provider_attempts"][10]["attempt_number"] = 999
        with self.assertRaisesRegex(RuntimeError, "ATTEMPT_LEDGER_MISMATCH"):
            reconcile_attempt_ledgers(None, trajectory, self.packet)


class ExternalKillRegressionTest(unittest.TestCase):
    def test_missing_measurement_with_durable_attempts_normalizes(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            jobs = root / "jobs"
            trial = jobs / "job" / "trial"
            agent = trial / "agent"
            verifier = trial / "verifier"
            agent.mkdir(parents=True)
            verifier.mkdir()
            attempts = [
                {"attempt_number": 1, "accounting_status": "COUNTED", "total_tokens": 12, "input_tokens": 10, "output_tokens": 2},
                {"attempt_number": 2, "accounting_status": "UNKNOWN", "total_tokens": None, "input_tokens": None, "output_tokens": None},
            ]
            (agent / "provider_attempts.json").write_text(json.dumps({"aggregate": {"accounting_status": "TOKEN_ACCOUNTING_INVALID", "attempt_count": 2, "total_provider_tokens": None}, "attempts": attempts}))
            (agent / "mini-swe-agent.trajectory.json").write_text(json.dumps({"info": {"provider_attempts": attempts[:1]}, "messages": []}))
            (trial / "result.json").write_text(json.dumps({
                "task_name": "terminal-bench/atrx-vep-crispr",
                "trial_name": "kill-fixture",
                "id": "fixture-id",
                "started_at": "2026-01-01T00:00:00Z",
                "finished_at": "2026-01-01T00:01:00Z",
                "verifier_result": {"rewards": {"reward": 0}},
                "exception_info": {"exception_type": "AgentTimeoutError", "exception_message": "externally terminated"},
            }))
            (trial / "exception.txt").write_text("AgentTimeoutError: externally terminated")
            (verifier / "reward.json").write_text('{"reward":0}')
            preflight = root / "preflight.json"
            preflight.write_text(json.dumps({"status": "PASS", "manifest_sha256": MANIFEST_SHA, "task_id": "atrx-vep-crispr", "condition": "A", "task_environment_identity_sha256": "fixture"}))
            out = root / "out"
            result = normalize(jobs_dir=jobs, preflight_path=preflight, task="atrx-vep-crispr", task_order=1, condition="A", condition_position=1, run_id="kill-test", output_dir=out)
            self.assertFalse(result["success"])
            self.assertEqual(result["evaluator_reward"], 0)
            self.assertEqual(result["provider_attempt_count"], 2)
            self.assertEqual(result["accounting_status"], "TOKEN_ACCOUNTING_INVALID")
            self.assertIsNone(result["provider_total_tokens"])
            self.assertEqual(result["agent_exception_type"], "AgentTimeoutError")
            self.assertFalse(result["measurement_present"])


class ResumeScheduleTests(unittest.TestCase):
    def test_exact_47_condition_resume_schedule(self):
        path = Path(__file__).with_name("resume_schedule.json")
        obj = json.loads(path.read_text(encoding="utf-8"))
        remaining = obj["remaining"]
        self.assertEqual(obj["remaining_count"], 47)
        self.assertEqual(len(remaining), 47)
        self.assertEqual(len({(x["task_id"], x["condition"]) for x in remaining}), 47)
        self.assertEqual(remaining[0], {"task_order": 1, "task_id": "atrx-vep-crispr", "condition": "B", "condition_position": 2})
        self.assertFalse(any(x["task_id"] == "atrx-vep-crispr" and x["condition"] == "A" for x in remaining))
        frozen = [
            (1,"atrx-vep-crispr","ABCD"),(2,"batched-eval-parity","BCDA"),(3,"cad-model","CDAB"),(4,"cargo-flight-dispatch","DABC"),
            (5,"coq-block-bound","ABCD"),(6,"cumulative-layout-shift","BCDA"),(7,"data-anonymization","CDAB"),(8,"live-database-cutover","DABC"),
            (9,"music-harmony","ABCD"),(10,"uefi-bootkit","BCDA"),(11,"production-planning","CDAB"),(12,"wdm-design","DABC"),
        ]
        expected = []
        for order, task, conditions in frozen:
            for position, condition in enumerate(conditions, 1):
                if not (order == 1 and condition == "A"):
                    expected.append({"task_order": order, "task_id": task, "condition": condition, "condition_position": position})
        self.assertEqual(remaining, expected)
        self.assertFalse(obj["preserved"]["rerun"])


class FailureContinuationTests(unittest.TestCase):
    def test_scientific_failures_continue(self):
        for value in ["TASK_FAILURE", "TOKEN_ACCOUNTING_INVALID", "AGENT_OR_HARNESS_EXCEPTION"]:
            self.assertFalse(must_stop_after_condition(value), value)

    def test_identity_implementation_and_missing_verifier_stop(self):
        for value in ["BENCHMARK_INVALID_IMPLEMENTATION_DEFECT", "INFRASTRUCTURE_INVALID_EXPERIMENT", "CONFIGURATION_INVALID", "VERIFIER_RESULT_MISSING", "UNRECOGNIZED"]:
            self.assertTrue(must_stop_after_condition(value), value)


if __name__ == "__main__":
    unittest.main()
