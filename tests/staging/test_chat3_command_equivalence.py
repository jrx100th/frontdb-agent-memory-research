from __future__ import annotations

import subprocess
from pathlib import Path

from minisweagent.memory.retrieve import RetrievalState, retrieve
from minisweagent.memory.store import MemoryEvent, MemoryStore, _normalize_command, _scientific_key


def mkstore(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "memory.sqlite")


def put(store: MemoryStore, *, step: int, command: str):
    return store.store(
        MemoryEvent(
            task_id="t",
            step_id=step,
            content="same command failure evidence",
            kind="TOOL",
            command=command,
            outcome="FAILED",
            memory_type="FAILED_APPROACH",
            verification_status="OBSERVED",
            importance=2,
        )
    )[0]


def candidate_ids(result) -> set[int]:
    return {x["memory_id"] for x in result.candidates}


def run_bash(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", command],
        text=True,
        capture_output=True,
        check=False,
    )


def test_c03_ascii_space_and_nbsp_are_distinct_scientific_command_identity(tmp_path):
    cmd_space = "echo x"
    cmd_nbsp = "echo\u00a0x"

    assert cmd_space != cmd_nbsp

    normal = run_bash(cmd_space)
    nbsp = run_bash(cmd_nbsp)
    assert normal.returncode == 0
    assert nbsp.returncode != normal.returncode

    # A lookup/scientific command representation must not compatibility-fold
    # shell-distinct raw commands into one identity.
    assert _normalize_command(cmd_space) != _normalize_command(cmd_nbsp)

    common = dict(
        content_fingerprint="0" * 64,
        memory_type="FAILED_APPROACH",
        verification_status="OBSERVED",
        outcome="FAILED",
        file_paths=[],
        file_fingerprints=[],
    )
    assert _scientific_key(command=cmd_space, **common) != _scientific_key(command=cmd_nbsp, **common)

    s = mkstore(tmp_path)
    a = put(s, step=1, command=cmd_nbsp)
    b = put(s, step=2, command=cmd_space)
    r = retrieve(
        "same command failure evidence",
        RetrievalState(task_id="t", current_step=10),
        2048,
        db_path=s.db_path,
    )
    assert {a.memory_id, b.memory_id} <= candidate_ids(r)
