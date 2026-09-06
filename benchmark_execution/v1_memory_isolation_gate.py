from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
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
    runtime = getattr(agent, "_memory_runtime", None)
    # This is the exact memory lifecycle hook executed by DefaultAgent.run()
    # before its first model query. No model query is permitted in this gate.
    if runtime is not None:
        runtime.start_task("provider-free-memory-gate", task_id="v1-memory-isolation-gate")
    files = sorted(str(p.relative_to(work)) for p in work.glob("memory*.sqlite*"))
    runtime_path = str(runtime.db_path.resolve()) if runtime is not None else None
    if model.query_calls != 0:
        raise RuntimeError("PROVIDER_CALL_OCCURRED_IN_MEMORY_ISOLATION_GATE")
    return {
        "condition": condition,
        "run_label": run_label,
        "base_path": str(base.resolve()),
        "runtime_path": runtime_path,
        "files": files,
        "provider_calls": model.query_calls,
        "memory_runtime_present": runtime is not None,
    }


def _has_table(path: str, table: str) -> bool:
    with sqlite3.connect(path) as con:
        row = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return row is not None


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

        if a["memory_runtime_present"] or a["runtime_path"] is not None or a["files"]:
            raise RuntimeError(f"V1_A_MEMORY_SIDE_EFFECT:{a}")
        if b["memory_runtime_present"] or b["runtime_path"] is not None or b["files"]:
            raise RuntimeError(f"V1_B_MEMORY_SIDE_EFFECT:{b}")

        scoped = [(c1, "memory.C.sqlite"), (c2, "memory.C.sqlite"), (d1, "memory.D.sqlite"), (d2, "memory.D.sqlite")]
        for rec, suffix in scoped:
            if not rec["memory_runtime_present"] or rec["runtime_path"] is None or not rec["runtime_path"].endswith(suffix):
                raise RuntimeError(f"V1_MEMORY_DB_SCOPE_INVALID:{rec}:{suffix}")
            if suffix not in rec["files"] or not Path(rec["runtime_path"]).is_file():
                raise RuntimeError(f"V1_MEMORY_DB_NOT_CREATED:{rec}:{suffix}")

        paths = [rec["runtime_path"] for rec, _ in scoped]
        if len(set(paths)) != 4:
            raise RuntimeError("V1_MEMORY_DB_NOT_FRESH_UNIQUE")
        inodes = {(Path(p).stat().st_dev, Path(p).stat().st_ino) for p in paths}
        if len(inodes) != 4:
            raise RuntimeError("V1_MEMORY_DB_FILESYSTEM_ALIAS")

        # Prove zero cross-condition/file state: mutate only C1 with a gate-only
        # sentinel table and require all other freshly-started runtimes remain untouched.
        sentinel = "v1_gate_isolation_sentinel"
        with sqlite3.connect(c1["runtime_path"]) as con:
            con.execute(f"CREATE TABLE {sentinel}(value TEXT NOT NULL)")
            con.execute(f"INSERT INTO {sentinel}(value) VALUES ('C1_ONLY')")
            con.commit()
        if not _has_table(c1["runtime_path"], sentinel):
            raise RuntimeError("V1_MEMORY_SENTINEL_WRITE_FAILED")
        for rec in (c2, d1, d2):
            if _has_table(rec["runtime_path"], sentinel):
                raise RuntimeError(f"V1_MEMORY_CROSS_CONDITION_STATE:{rec['condition']}:{rec['run_label']}")

        result = {
            "schema_version": 2,
            "a_b_no_memory": True,
            "c_d_fresh_unique_condition_scoped": True,
            "zero_cross_condition_state": True,
            "provider_calls": 0,
            "records": [a, b, c1, c2, d1, d2],
            "distinct_db_file_count": 4,
            "cross_state_sentinel_source": c1["runtime_path"],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        print("A_B_NO_MEMORY_TEST=PASS runtime_side_effects=0 db_files=0")
        print("C_D_FRESH_DB_TEST=PASS distinct_db_files=4 cross_condition_state=0")
        print("PROVIDER_CALLS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
