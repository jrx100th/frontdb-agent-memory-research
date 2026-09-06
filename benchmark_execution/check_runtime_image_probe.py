from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs-dir", type=Path, required=True)
    ap.add_argument("--expected", required=True)
    ap.add_argument("--task", required=True)
    args = ap.parse_args()

    markers = list(args.jobs_dir.rglob("provider_free_runtime_image_probe.json"))
    if len(markers) != 1:
        raise RuntimeError(f"EXPECTED_ONE_RUNTIME_IMAGE_PROBE_MARKER_FOUND_{len(markers)}")
    marker = json.loads(markers[0].read_text(encoding="utf-8"))
    actual = marker.get("actual_runtime_image_id")
    expected = marker.get("expected_runtime_image_id")
    print(f"PROBE_EXPECTED={expected}")
    print(f"PROBE_ACTUAL={actual}")
    if expected != args.expected or actual != args.expected or marker.get("match") is not True:
        raise RuntimeError(f"INFRASTRUCTURE_INVALID_RUNTIME_IMAGE_DRIFT expected={args.expected} actual={actual}")
    if marker.get("provider_calls") != 0 or marker.get("benchmark_agent_runs") != 0 or marker.get("scientific_results_observed") != 0:
        raise RuntimeError("PROVIDER_FREE_BOUNDARY_VIOLATION")

    trial_results = []
    for path in args.jobs_dir.rglob("result.json"):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if obj.get("task_name") in {args.task, f"terminal-bench/{args.task}"} and obj.get("trial_name"):
            trial_results.append((path, obj))
    if len(trial_results) != 1:
        raise RuntimeError(f"EXPECTED_ONE_PROBE_TRIAL_RESULT_FOUND_{len(trial_results)}")
    path, trial = trial_results[0]
    if trial.get("exception_info") is not None:
        raise RuntimeError(f"PROBE_TRIAL_EXCEPTION:{trial.get('exception_info')}")
    exception_files = list(args.jobs_dir.rglob("exception.txt"))
    if exception_files:
        text = " | ".join(p.read_text(encoding="utf-8", errors="replace")[-1000:] for p in exception_files)
        raise RuntimeError(f"PROBE_EXCEPTION_FILE_PRESENT:{text}")
    print(f"RUNTIME_IMAGE_GATE_PASS={actual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
