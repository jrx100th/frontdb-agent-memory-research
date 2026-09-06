from __future__ import annotations

FATAL_FAILURE_CLASSES = {
    "BENCHMARK_INVALID_IMPLEMENTATION_DEFECT",
    "INFRASTRUCTURE_INVALID_EXPERIMENT",
    "CONFIGURATION_INVALID",
    "VERIFIER_RESULT_MISSING",
}

CONTINUABLE_OUTCOMES = {
    None,
    "",
    "TASK_FAILURE",
    "TOKEN_ACCOUNTING_INVALID",
    "AGENT_OR_HARNESS_EXCEPTION",
}


def must_stop_after_condition(failure_class: str | None) -> bool:
    """Workflow continuation policy; does not change scientific classification."""
    if failure_class in FATAL_FAILURE_CLASSES:
        return True
    if failure_class in CONTINUABLE_OUTCOMES:
        return False
    return True
