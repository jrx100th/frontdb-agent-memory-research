from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from minisweagent.agents.default import DefaultAgent


class NoQueryModel:
    def __init__(self):
        self.query_calls = 0

    def query(self, messages):
        self.query_calls += 1
        raise AssertionError("PROVIDER_QUERY_FORBIDDEN_IN_MEMORY_ISOLATION_GATE")

    def get_template_vars(self):
        return {}


class NoExecEnvironment:
    def execute(self, action):
        raise AssertionError("ENVIRONMENT_EXECUTION_FORBIDDEN_IN_MEMORY_ISOLATION_GATE")

    def get_template_vars(self):
        return {}


def instantiate(root: Path, condition: str, run_label: str) -> dict:
    work = root / f"{condition}-{run_label}"
    work.mkdir(parents=True, exist_ok=False)
    base = work / "memory.sqlite"
    model = NoQueryModel()
    agent = DefaultAgent(
        model,
        NoExecEnvironment(),
        system_template="system",
        instance_template="task",
        cost_limit=0.0,
        memory_enabled=True,
        memory_db_path=base,
        memory_task_id="v1-memory-isolation-gate",
        memory_workspace=work,
        benchmark_condition=condition,
    )
    files = sorted(str(p.relative_to(work)) for p in work.glob("memory*.sqlite*"))
    runtime = getattr(agent, "_memory_runtime", None)
    runtime_path = str(runtime.db_path) if runtime is not None else None
    if model.query_calls != 0:
        raise RuntimeError("PROVIDER_CALL_OCCURRED_IN_MEMORY_ISOLATION_GATE")
    return {
        "condition": condition,
        "run_label": run_label,
        "base_path": str(base),
        "runtime_path": runtime_path,
        "files": files,
        "provider_calls": model.query_calls,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    with TemporaryDirectory() as td:
        root = Path(td)
        a = instantiate(root, "A", "1")
        b = instantiate(root, "B", "1")
        c1 = instantiate(root, "C", "1")
        c2 = instantiate(root, "C", "2")
        d1 = instantiate(root, "D", "1")
        d2 = instantiate(root, "D", "2")

        if a["runtime_path"] is not None or a["files"]:
            raise RuntimeError(f"V1_A_MEMORY_DB_SIDE_EFFECT:{a}")
        if b["runtime_path"] is not None or b["files"]:
            raise RuntimeError(f"V1_B_MEMORY_DB_SIDE_EFFECT:{b}")
        for rec, suffix in [(c1, "memory.C.sqlite"), (c2, "memory.C.sqlite"), (d1, "memory.D.sqlite"), (d2, "memory.D.sqlite")]:
            if rec["runtime_path"] is None or not rec["runtime_path"].endswith(suffix):
                raise RuntimeError(f"V1_MEMORY_DB_SCOPE_INVALID:{rec}:{suffix}")
            if suffix not in rec["files"]:
                raise RuntimeError(f"V1_MEMORY_DB_NOT_CREATED:{rec}:{suffix}")
        if len({c1["runtime_path"], c2["runtime_path"], d1["runtime_path"], d2["runtime_path"]}) != 4:
            raise RuntimeError("V1_MEMORY_DB_NOT_FRESH_UNIQUE")

        result = {
            "schema_version": 1,
            "a_b_no_memory": True,
            "c_d_fresh_unique_condition_scoped": True,
            "provider_calls": 0,
            "records": [a, b, c1, c2, d1, d2],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        print("A_B_NO_MEMORY_TEST=PASS")
        print("C_D_FRESH_DB_TEST=PASS")
        print("PROVIDER_CALLS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
