from __future__ import annotations

import hashlib
import importlib
import json
import os
import time
from pathlib import Path

from minisweagent.memory.store import MemoryEvent, MemoryStore
from minisweagent.memory.retrieve import RetrievalState, retrieve
from minisweagent.memory.fingerprint import fingerprint

fpmod = importlib.import_module("minisweagent.memory.fingerprint")


def mkstore(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "memory.sqlite")


def put(store: MemoryStore, *, task: str = "t", step: int = 1, content: str = "x", kind: str = "TOOL", **kw):
    return store.store(MemoryEvent(task_id=task, step_id=step, content=content, kind=kind, **kw))[0]


def state(step: int = 20000, **kw) -> RetrievalState:
    return RetrievalState(task_id="t", current_step=step, **kw)


def selected_ids(result) -> list[int]:
    return [x["memory_id"] for x in result.selected]


def bulk_rows(store: MemoryStore, rows: list[tuple[int, str, str | None, str | None]]) -> None:
    """Fast valid-row fixture insertion; schema triggers still populate FTS."""
    values = []
    for step, content, command, outcome in rows:
        values.append(
            (
                "t",
                step,
                "ERROR" if outcome == "FAILED" else "TOOL_RESULT",
                content,
                None,
                "[]",
                command,
                outcome,
                "OBSERVED",
                1,
                len(content.encode("utf-8")),
                hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "[]",
                None,
            )
        )
    with store.connect() as con:
        con.executemany(
            """INSERT INTO memories(task_id,step_id,memory_type,content,source_ref,file_paths,command,outcome,
               verification_status,importance,token_count,fingerprint,file_fingerprints,supersedes,invalidated_by)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)""",
            values,
        )


def test_r01_over_4200_exact_duplicate_fts_rows_cannot_starve_distinct_target(tmp_path):
    s = mkstore(tmp_path)
    target = put(
        s,
        step=1,
        content="alpha beta unique verified target",
        memory_type="TEST_RESULT",
        verification_status="VERIFIED",
        importance=2,
    )
    bulk_rows(s, [(100 + i, "alpha beta duplicate", None, "FAILED") for i in range(4200)])
    r = retrieve("alpha beta", state(), 2048, db_path=s.db_path)
    assert target.memory_id in selected_ids(r), "R01: exact duplicate flood starved distinct target"


def test_r05_deep_failed_command_recall_normalizes_stored_whitespace(tmp_path):
    s = mkstore(tmp_path)
    target = put(
        s,
        step=1,
        content="historic command failure",
        command="  pytest tests/a.py  ",
        outcome="FAILED",
        memory_type="FAILED_APPROACH",
        verification_status="OBSERVED",
        importance=2,
    )
    bulk_rows(s, [(100 + i, f"noise row {i}", None, None) for i in range(300)])
    r = retrieve(
        "unrelated recovery planning",
        state(failed_command_signature="pytest tests/a.py"),
        2048,
        db_path=s.db_path,
    )
    assert target.memory_id in selected_ids(r), "R05: stored command whitespace broke deep recall"


def test_r06b_explicit_error_signature_is_exact_not_substring(tmp_path):
    s = mkstore(tmp_path)
    false_match = put(s, step=1, content="failure marker E_SIG_EXTRA", returncode=1)
    r = retrieve(
        "unrelated recovery planning",
        state(error_signature="E_SIG"),
        2048,
        db_path=s.db_path,
    )
    assert false_match.memory_id not in selected_ids(r), "R06B: E_SIG falsely matched E_SIG_EXTRA"


def test_r11_same_text_different_file_state_remains_distinct(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("state-a", encoding="utf-8")
    b.write_text("state-b", encoding="utf-8")
    s = mkstore(tmp_path)
    first = put(
        s,
        step=1,
        content="same scientific file evidence",
        memory_type="TEST_RESULT",
        verification_status="VERIFIED",
        importance=2,
        file_paths=["a.txt"],
        workspace=str(tmp_path),
    )
    second = put(
        s,
        step=2,
        content="same scientific file evidence",
        memory_type="TEST_RESULT",
        verification_status="VERIFIED",
        importance=2,
        file_paths=["b.txt"],
        workspace=str(tmp_path),
    )
    r = retrieve(
        "same scientific file evidence",
        state(step=10, workspace=str(tmp_path), file_paths=["a.txt", "b.txt"]),
        2048,
        db_path=s.db_path,
    )
    got = selected_ids(r)
    assert first.memory_id in got and second.memory_id in got, "R11: different file-state evidence deduplicated"


def test_r13_symlink_aba_with_reused_identity_fails_closed(tmp_path, monkeypatch):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    link = tmp_path / "link.txt"
    a.write_text("stable-target-a", encoding="utf-8")
    b.write_text("temporary-target-b", encoding="utf-8")
    link.symlink_to(a.name)

    original_read = fpmod.os.read
    fired = False

    def racing_read(fd: int, n: int) -> bytes:
        nonlocal fired
        block = original_read(fd, n)
        if block and not fired:
            fired = True
            link.unlink()
            link.symlink_to(b.name)
            link.unlink()
            link.symlink_to(a.name)
            # Force an observable path-entry timestamp change while ending at A.
            stamp = time.time_ns() + 5_000_000
            os.utime(link, ns=(stamp, stamp), follow_symlinks=False)
        return block

    monkeypatch.setattr(fpmod.os, "read", racing_read)
    # Deterministically model the inode-reuse condition observed by Chat3.
    monkeypatch.setattr(fpmod, "_same_identity", lambda _a, _b: True)
    current = fingerprint("link.txt", tmp_path)
    assert fired
    assert current.status == "UNSTABLE", "R13: observable A->B->A ABA returned OK/FRESH-capable"


def test_r17_old_strasse_casefold_only_record_is_index_retrievable(tmp_path):
    s = mkstore(tmp_path)
    target = put(s, step=1, content="straße")
    bulk_rows(s, [(100 + i, f"newer unrelated row {i}", None, None) for i in range(300)])
    r = retrieve("STRASSE", state(), 2048, db_path=s.db_path)
    assert target.memory_id in selected_ids(r), "R17: old normalization-only evidence was recency bounded"


def test_r27_supplemental_explicit_candidates_cannot_monopolize_pool(tmp_path):
    s = mkstore(tmp_path)
    target = put(
        s,
        step=1,
        content="strong ordinary lexical target",
        memory_type="TEST_RESULT",
        verification_status="VERIFIED",
        importance=2,
    )
    bulk_rows(s, [(100 + i, f"E_POOL explicit decoy {i}", None, "FAILED") for i in range(40)])
    r = retrieve(
        "strong ordinary lexical target",
        state(error_signature="E_POOL"),
        2048,
        db_path=s.db_path,
    )
    assert target.memory_id in selected_ids(r), "R27: explicit candidates monopolized the 40-candidate pool"
