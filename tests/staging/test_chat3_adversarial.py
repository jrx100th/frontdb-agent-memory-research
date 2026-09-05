from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from minisweagent.memory.store import MemoryEvent, MemoryStore
from minisweagent.memory.retrieve import RetrievalState, retrieve
from minisweagent.memory.fingerprint import MAX_FILE_BYTES, compare_fingerprint, fingerprint
from minisweagent.memory.context_builder import build_context, canonical_json, memory_message, serialized_message_units
from minisweagent.instrumentation.token_logger import INVALID, extract_provider_usage

fpmod = importlib.import_module("minisweagent.memory.fingerprint")


def mkstore(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "memory.sqlite")


def put(store: MemoryStore, *, task: str = "t", step: int = 1, content: str = "x", kind: str = "TOOL", **kw):
    return store.store(MemoryEvent(task_id=task, step_id=step, content=content, kind=kind, **kw))[0]


def state(step: int = 1000, **kw) -> RetrievalState:
    return RetrievalState(task_id="t", current_step=step, **kw)


def _selected_ids(result) -> list[int]:
    return [x["memory_id"] for x in result.selected]


def test_a01_duplicate_candidate_starvation(tmp_path):
    s = mkstore(tmp_path)
    target = put(
        s,
        step=1,
        content="alpha beta unique verified target",
        memory_type="TEST_RESULT",
        verification_status="VERIFIED",
        importance=2,
    )
    for i in range(25):
        put(s, step=10 + i, content="alpha beta duplicate", returncode=1)
    r = retrieve("alpha beta", state(), 2048, db_path=s.db_path)
    assert target.memory_id in _selected_ids(r)


def test_a02_old_explicit_error_beyond_supplemental_window(tmp_path):
    s = mkstore(tmp_path)
    target = put(s, step=1, content="historic crash E_OLDRACE", returncode=1)
    for i in range(205):
        put(s, step=10 + i, content=f"recent unrelated telemetry row {i}")
    r = retrieve(
        "recovery planning",
        state(error_signature="E_OLDRACE"),
        2048,
        db_path=s.db_path,
    )
    assert target.memory_id in _selected_ids(r)


def test_a03_verified_numeric_correction_not_suppressed(tmp_path):
    s = mkstore(tmp_path)
    old = put(s, step=1, content="timeout 30", kind="ASSISTANT")
    new = put(
        s,
        step=2,
        content=(
            "timeout 60 the and for with that this from into your you are was were has have had not but can will all our out use using then than when where what"
        ),
        memory_type="TEST_RESULT",
        verification_status="VERIFIED",
        importance=1,
    )
    r = retrieve("timeout", state(step=10), 900, db_path=s.db_path)
    ids = _selected_ids(r)
    assert new.memory_id in ids
    assert old.memory_id not in ids


def test_a04_exact_content_metadata_conflict_not_collapsed(tmp_path):
    s = mkstore(tmp_path)
    failed = put(
        s,
        step=1,
        content="same command result payload",
        command="pytest -q",
        outcome="FAILED",
        memory_type="FAILED_APPROACH",
        verification_status="OBSERVED",
        importance=2,
    )
    passed = put(
        s,
        step=2,
        content="same command result payload",
        command="pytest -q",
        outcome="PASSED",
        memory_type="TEST_RESULT",
        verification_status="VERIFIED",
        importance=2,
    )
    r = retrieve("same command result payload", state(step=10), 2048, db_path=s.db_path)
    ids = _selected_ids(r)
    assert failed.memory_id in ids
    assert passed.memory_id in ids


def test_a05_symlink_retarget_during_hash_fails_closed(tmp_path, monkeypatch):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    link = tmp_path / "link.txt"
    a.write_text("stable-old-target", encoding="utf-8")
    b.write_text("new-target-data", encoding="utf-8")
    link.symlink_to(a.name)
    old = fingerprint("link.txt", tmp_path).to_dict()

    original_read = fpmod.os.read
    switched = False

    def racing_read(fd: int, n: int) -> bytes:
        nonlocal switched
        block = original_read(fd, n)
        if block and not switched:
            switched = True
            link.unlink()
            link.symlink_to(b.name)
        return block

    monkeypatch.setattr(fpmod.os, "read", racing_read)
    current = fingerprint("link.txt", tmp_path)
    assert switched
    assert compare_fingerprint(old, current) != "FRESH"


def test_a06_unicode_casefold_candidate_recall(tmp_path):
    s = mkstore(tmp_path)
    rec = put(s, step=1, content="straße")
    r = retrieve("STRASSE", state(step=10), 2048, db_path=s.db_path)
    assert rec.memory_id in _selected_ids(r)


def test_a07_inconsistent_provider_total_is_invalid():
    usage = extract_provider_usage(
        {"id": "r1", "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 999}},
        attempt_id="a1",
        retry_index=0,
    )
    assert usage.accounting_status == INVALID
    assert usage.total_tokens == 999


def test_a08_nested_cache_and_reasoning_details_preserved():
    usage = extract_provider_usage(
        {
            "id": "r2",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 4,
                "total_tokens": 14,
                "prompt_tokens_details": {"cached_tokens": 3},
                "completion_tokens_details": {"reasoning_tokens": 2},
            },
        },
        attempt_id="a2",
        retry_index=0,
    )
    assert usage.accounting_status == "OK"
    assert usage.cached_fields == {"prompt_tokens_details": {"cached_tokens": 3}}
    assert usage.reasoning_fields == {"completion_tokens_details": {"reasoning_tokens": 2}}
    assert usage.total_tokens == 14


def test_a09_exact_64_mib_boundary(tmp_path):
    p = tmp_path / "boundary.bin"
    with p.open("wb") as f:
        f.truncate(MAX_FILE_BYTES)
    exact = fingerprint("boundary.bin", tmp_path)
    assert exact.status == "OK"
    assert exact.size == MAX_FILE_BYTES
    with p.open("r+b") as f:
        f.truncate(MAX_FILE_BYTES + 1)
    assert fingerprint("boundary.bin", tmp_path).status == "TOO_LARGE"


def _records_for_exact_envelope(target: int) -> list[dict]:
    empty = [{"content": ""}]
    overhead = serialized_message_units(empty)
    assert target >= overhead
    records = [{"content": "x" * (target - overhead)}]
    assert len(canonical_json(memory_message(records)).encode("utf-8")) == target
    return records


@pytest.mark.parametrize("target", [2047, 2048, 2049])
def test_a10_independent_envelope_boundaries(target):
    records = _records_for_exact_envelope(target)
    assert serialized_message_units(records) == target


def test_a11_multi_tool_complete_step_and_incomplete_trailing_step():
    history = [
        {
            "role": "assistant",
            "content": "run two tools",
            "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "bash", "arguments": "{}"}},
                {"id": "c2", "type": "function", "function": {"name": "bash", "arguments": "{}"}},
            ],
        },
        {"role": "tool", "content": "one", "tool_call_id": "c1"},
        {"role": "tool", "content": "two", "tool_call_id": "c2"},
        {"role": "assistant", "content": "incomplete trailing", "tool_calls": [{"id": "c3"}]},
    ]
    msgs = build_context("S", "T", history, None)
    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "tool", "tool"]
    assert [m.get("tool_call_id") for m in msgs if m["role"] == "tool"] == ["c1", "c2"]
    assert all(m.get("content") != "incomplete trailing" for m in msgs)


def test_a12_missing_provider_usage_never_falls_back():
    usage = extract_provider_usage(
        {"id": "r3", "choices": [{"message": {"content": "possibly generated"}}]},
        attempt_id="a3",
        retry_index=0,
        possibly_generated=True,
    )
    assert usage.accounting_status == INVALID
    assert usage.input_tokens is None
    assert usage.output_tokens is None
    assert usage.total_tokens is None
