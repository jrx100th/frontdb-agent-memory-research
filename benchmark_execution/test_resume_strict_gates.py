from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest

from benchmark_execution.completion_marker import build_completion_record
from benchmark_execution.postprocess_resume import MANIFEST_SHA, normalize


class ActualExternalKillGate(unittest.TestCase):
    def test_process_killed_after_durable_ledger_before_measurement(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            trial = root / "jobs" / "job" / "trial"
            agent = trial / "agent"
            verifier = trial / "verifier"
            agent.mkdir(parents=True)
            verifier.mkdir()
            producer = root / "producer.py"
            producer.write_text(
                "import json,pathlib,time\n"
                "p=pathlib.Path(__import__('sys').argv[1]); p.mkdir(parents=True,exist_ok=True)\n"
                "attempts=[{'attempt_number':1,'accounting_status':'COUNTED','total_tokens':12,'input_tokens':10,'output_tokens':2},"
                "{'attempt_number':2,'accounting_status':'UNKNOWN','total_tokens':None,'input_tokens':None,'output_tokens':None}]\n"
                "(p/'provider_attempts.json').write_text(json.dumps({'aggregate':{'accounting_status':'TOKEN_ACCOUNTING_INVALID','attempt_count':2,'total_provider_tokens':None},'attempts':attempts}))\n"
                "(p/'mini-swe-agent.trajectory.json').write_text(json.dumps({'info':{'provider_attempts':attempts[:1]},'messages':[]}))\n"
                "(p/'ready').write_text('ready')\n"
                "time.sleep(60)\n"
                "(p/'measurement.json').write_text('{}')\n",
                encoding="utf-8",
            )
            proc = subprocess.Popen([sys.executable, str(producer), str(agent)])
            deadline = time.time() + 10
            while not (agent / "ready").exists() and time.time() < deadline:
                time.sleep(0.02)
            self.assertTrue((agent / "ready").exists())
            proc.terminate()
            proc.wait(timeout=5)
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse((agent / "measurement.json").exists())

            (trial / "result.json").write_text(json.dumps({
                "task_name":"terminal-bench/atrx-vep-crispr","trial_name":"actual-kill-fixture","id":"actual-kill",
                "started_at":"2026-01-01T00:00:00Z","finished_at":"2026-01-01T00:01:00Z",
                "verifier_result":{"rewards":{"reward":0}},
                "exception_info":{"exception_type":"AgentTimeoutError","exception_message":"terminated before measurement flush"},
            }), encoding="utf-8")
            (trial / "exception.txt").write_text("AgentTimeoutError: terminated before measurement flush", encoding="utf-8")
            (verifier / "reward.json").write_text('{"reward":0}', encoding="utf-8")
            preflight = root / "preflight.json"
            preflight.write_text(json.dumps({
                "status":"PASS","manifest_sha256":MANIFEST_SHA,"task_id":"atrx-vep-crispr","condition":"B",
                "task_environment_identity_sha256":"fixture"
            }), encoding="utf-8")
            image = root / "image.txt"
            image.write_text("sha256:" + "a"*64 + "\n", encoding="utf-8")
            out = root / "evidence"
            result = normalize(jobs_dir=root/"jobs", preflight_path=preflight, task="atrx-vep-crispr", task_order=1,
                               condition="B", condition_position=2, run_id="actual-kill", output_dir=out,
                               runtime_image_ledger=image)
            self.assertFalse(result["success"])
            self.assertEqual(result["evaluator_reward"], 0)
            self.assertEqual(result["provider_attempt_count"], 2)
            self.assertEqual(result["accounting_status"], "TOKEN_ACCOUNTING_INVALID")
            self.assertEqual(result["agent_exception_type"], "AgentTimeoutError")
            self.assertFalse(result["measurement_present"])
            self.assertTrue((out / "provider_attempts.json").exists())
            self.assertTrue((out / "run_result.json").exists())

            marker = build_completion_record(result)
            marker_path = out / "condition_complete.json"
            marker_path.write_text(json.dumps(marker, sort_keys=True) + "\n", encoding="utf-8")
            self.assertEqual(json.loads(marker_path.read_text())["status"], "COMPLETE")
            self.assertTrue(marker["continuation_permitted"])

            schedule = json.loads(Path(__file__).with_name("resume_schedule.json").read_text(encoding="utf-8"))["remaining"]
            self.assertEqual(schedule[0]["condition"], "B")
            self.assertEqual(schedule[1]["condition"], "C")
            self.assertEqual(schedule[1]["task_id"], "atrx-vep-crispr")


class CompletionStopGate(unittest.TestCase):
    def _base(self, failure_class):
        return {
            "experiment_manifest_sha256": MANIFEST_SHA,
            "run_id":"fixture","task_id":"atrx-vep-crispr","task_order":1,"condition":"B","condition_order_position":2,
            "success":False,"evaluator_result":{"rewards":{"reward":0}},"evaluator_reward":0,
            "failure_class":failure_class,"accounting_status":"VALID","provider_attempt_count":1,
            "task_environment_image_digest":"sha256:"+"a"*64,
        }

    def test_legitimate_task_failure_gets_completion_marker(self):
        marker = build_completion_record(self._base("TASK_FAILURE"))
        self.assertEqual(marker["status"], "COMPLETE")
        self.assertTrue(marker["continuation_permitted"])

    def test_identity_configuration_and_implementation_defects_do_not_get_marker(self):
        for value in ["INFRASTRUCTURE_INVALID_EXPERIMENT","CONFIGURATION_INVALID","BENCHMARK_INVALID_IMPLEMENTATION_DEFECT","VERIFIER_RESULT_MISSING"]:
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                build_completion_record(self._base(value))


if __name__ == "__main__":
    unittest.main()
