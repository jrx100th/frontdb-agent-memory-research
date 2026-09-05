from __future__ import annotations

from pathlib import Path

from minisweagent.memory.retrieve import RetrievalState, retrieve
from minisweagent.memory.store import MemoryEvent, MemoryStore, _normalize_command


def test_lookup_key_collision_does_not_collapse_raw_scientific_variants(tmp_path: Path):
    db = tmp_path / "memory.sqlite"
    store = MemoryStore(db)
    canonical = "echo x"
    boundary = "  echo x   "
    assert _normalize_command(canonical) == _normalize_command(boundary)

    a = store.store(MemoryEvent(
        task_id="t", step_id=1, content="same raw collision evidence", kind="TOOL",
        command=canonical, outcome="FAILED", memory_type="FAILED_APPROACH",
        verification_status="OBSERVED", importance=2,
    ))[0]
    b = store.store(MemoryEvent(
        task_id="t", step_id=2, content="same raw collision evidence", kind="TOOL",
        command=boundary, outcome="FAILED", memory_type="FAILED_APPROACH",
        verification_status="OBSERVED", importance=2,
    ))[0]

    result = retrieve(
        "same raw collision evidence",
        RetrievalState(task_id="t", current_step=10),
        2048,
        db_path=db,
    )
    ids = {row["memory_id"] for row in result.candidates}
    assert {a.memory_id, b.memory_id} <= ids
