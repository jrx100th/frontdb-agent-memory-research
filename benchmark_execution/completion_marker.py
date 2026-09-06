from __future__ import annotations

from benchmark_execution.resume_control import must_stop_after_condition


def build_completion_record(run_result: dict) -> dict:
    if run_result.get("evaluator_result") is None:
        raise RuntimeError("VERIFIER_RESULT_MISSING")
    failure_class = run_result.get("failure_class")
    if must_stop_after_condition(failure_class):
        raise RuntimeError(f"NONCONTINUABLE_CONDITION:{failure_class}")
    required = ("experiment_manifest_sha256", "run_id", "task_id", "task_order", "condition", "condition_order_position")
    if any(run_result.get(k) is None for k in required):
        raise RuntimeError("CONDITION_COMPLETION_IDENTITY_MISSING")
    return {
        "schema_version": 1,
        "status": "COMPLETE",
        "continuation_permitted": True,
        "experiment_manifest_sha256": run_result["experiment_manifest_sha256"],
        "run_id": run_result["run_id"],
        "task_id": run_result["task_id"],
        "task_order": run_result["task_order"],
        "condition": run_result["condition"],
        "condition_order_position": run_result["condition_order_position"],
        "success": run_result.get("success"),
        "evaluator_reward": run_result.get("evaluator_reward"),
        "failure_class": failure_class,
        "accounting_status": run_result.get("accounting_status"),
        "provider_attempt_count": run_result.get("provider_attempt_count"),
        "task_environment_image_digest": run_result.get("task_environment_image_digest"),
    }
