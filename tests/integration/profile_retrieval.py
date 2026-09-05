from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time

os.environ.setdefault("MSWEA_SILENT_STARTUP", "1")

from minisweagent.memory.retrieve import RetrievalState, retrieve
from minisweagent.memory.store import MemoryEvent, MemoryStore


def profile_case(rows: int, matching: int) -> dict:
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "memory.sqlite"
        store = MemoryStore(db)
        for i in range(rows):
            match = i < matching
            content = "perfneedle duplicate evidence" if match else f"noise row {i} unrelated"
            store.store(
                MemoryEvent(
                    task_id="perf",
                    step_id=i + 1,
                    content=content,
                    kind="TOOL",
                    memory_type="ERROR" if match else "TOOL_RESULT",
                    verification_status="OBSERVED",
                    importance=2 if match else 1,
                )
            )
        state = RetrievalState(task_id="perf", current_step=rows + 100, task_text="perfneedle evidence")
        started = time.perf_counter()
        result = retrieve("perfneedle evidence", state, 2048, db_path=db)
        elapsed = time.perf_counter() - started
        return {
            "db_rows": rows,
            "matching_rows": matching,
            "candidate_count": len(result.candidates),
            "selected_count": len(result.selected),
            "retrieval_seconds": elapsed,
            "db_size_bytes": db.stat().st_size,
        }


def main() -> None:
    cases = {
        "ordinary": profile_case(12, 3),
        "100": profile_case(100, 100),
        "1000": profile_case(1000, 1000),
        "10000": profile_case(10000, 10000),
    }
    print(json.dumps(cases, sort_keys=True))
    Path("integration_artifacts").mkdir(exist_ok=True)
    Path("integration_artifacts/performance.json").write_text(
        json.dumps(cases, indent=2, sort_keys=True), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
