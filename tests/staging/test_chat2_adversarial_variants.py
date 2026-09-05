from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from minisweagent.memory.store import MemoryEvent, MemoryStore
from minisweagent.memory.retrieve import RetrievalState, retrieve
from minisweagent.memory.fingerprint import compare_fingerprint, fingerprint
from minisweagent.instrumentation.token_logger import INVALID, extract_provider_usage

fpmod = importlib.import_module("minisweagent.memory.fingerprint")


def mkstore(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "memory.sqlite")


def put(store: MemoryStore, *, step: int = 1, content: str = "x", kind: str = "TOOL", **kw):
    return store.store(MemoryEvent(task_id="t", step_id=step, content=content, kind=kind, **kw))[0]


def state(step: int = 5000, **kw) -> RetrievalState:
    return RetrievalState(task_id="t", current_step=step, **kw)


def ids(result) -> list[int]:
    return [x["memory_id"] for x in result.selected]


def test_duplicate_flood_100_does_not_starve_unique_target(tmp_path):
    s = mkstore(tmp_path)
    target = put(s, step=1, content="gamma delta unique target", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2)
    for i in range(100):
        put(s, step=100 + i, content="gamma delta duplicate", returncode=1)
    assert target.memory_id in ids(retrieve("gamma delta", state(), 2048, db_path=s.db_path))


@pytest.mark.parametrize("intervening", [201, 500, 1000])
def test_old_explicit_error_recall_at_multiple_depths(tmp_path, intervening):
    s = mkstore(tmp_path)
    target = put(s, step=1, content=f"old exact signature E_DEPTH_{intervening}", returncode=1)
    for i in range(intervening):
        put(s, step=10 + i, content=f"noise record {i}")
    r = retrieve("unrelated planning", state(error_signature=f"E_DEPTH_{intervening}"), 2048, db_path=s.db_path)
    assert target.memory_id in ids(r)


def test_numeric_differences_remain_distinct_for_unverified_hypotheses(tmp_path):
    s = mkstore(tmp_path)
    a = put(s, step=1, content="retry timeout 30", kind="ASSISTANT")
    b = put(s, step=2, content="retry timeout 60", kind="ASSISTANT")
    got = ids(retrieve("retry timeout", state(step=10), 2048, db_path=s.db_path))
    assert a.memory_id in got and b.memory_id in got


def test_multiple_verified_numeric_contradictions_remain_distinct(tmp_path):
    s = mkstore(tmp_path)
    a = put(s, step=1, content="verified timeout 30", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2)
    b = put(s, step=2, content="verified timeout 60", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2)
    got = ids(retrieve("verified timeout", state(step=10), 2048, db_path=s.db_path))
    assert a.memory_id in got and b.memory_id in got


def test_same_text_outcome_difference_remains_distinct(tmp_path):
    s = mkstore(tmp_path)
    a = put(s, step=1, content="build outcome payload", command="make", outcome="FAILED", memory_type="FAILED_APPROACH", verification_status="OBSERVED", importance=2)
    b = put(s, step=2, content="build outcome payload", command="make", outcome="PASSED", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2)
    got = ids(retrieve("build outcome payload", state(step=10), 2048, db_path=s.db_path))
    assert a.memory_id in got and b.memory_id in got


def _race_on_first_read(monkeypatch, callback):
    original = fpmod.os.read
    fired = False
    def read(fd, n):
        nonlocal fired
        block = original(fd, n)
        if block and not fired:
            fired = True
            callback()
        return block
    monkeypatch.setattr(fpmod.os, "read", read)
    return lambda: fired


def test_symlink_inside_to_inside_same_bytes_is_unstable(tmp_path, monkeypatch):
    a = tmp_path / "a"; b = tmp_path / "b"; link = tmp_path / "link"
    a.write_text("same-bytes"); b.write_text("same-bytes"); link.symlink_to(a.name)
    old = fingerprint("link", tmp_path).to_dict()
    def swap():
        link.unlink(); link.symlink_to(b.name)
    fired = _race_on_first_read(monkeypatch, swap)
    cur = fingerprint("link", tmp_path)
    assert fired() and cur.status == "UNSTABLE" and compare_fingerprint(old, cur) == "UNKNOWN"


def test_symlink_inside_to_outside_during_hash_is_unstable(tmp_path, monkeypatch):
    a = tmp_path / "a"; outside = tmp_path.parent / "outside-frontdb-race"; link = tmp_path / "link"
    a.write_text("inside"); outside.write_text("outside"); link.symlink_to(a.name)
    old = fingerprint("link", tmp_path).to_dict()
    def swap():
        link.unlink(); link.symlink_to(outside)
    fired = _race_on_first_read(monkeypatch, swap)
    try:
        cur = fingerprint("link", tmp_path)
        assert fired() and cur.status == "UNSTABLE" and compare_fingerprint(old, cur) == "UNKNOWN"
    finally:
        outside.unlink(missing_ok=True)


def test_regular_file_delete_recreate_during_hash_is_unstable(tmp_path, monkeypatch):
    p = tmp_path / "state.txt"; p.write_text("old inode payload")
    old = fingerprint("state.txt", tmp_path).to_dict()
    def replace():
        p.unlink(); p.write_text("new inode payload")
    fired = _race_on_first_read(monkeypatch, replace)
    cur = fingerprint("state.txt", tmp_path)
    assert fired() and cur.status == "UNSTABLE" and compare_fingerprint(old, cur) == "UNKNOWN"


def test_provider_additive_total_valid():
    u = extract_provider_usage({"usage":{"prompt_tokens":10,"completion_tokens":4,"total_tokens":14}}, attempt_id="v1", retry_index=0)
    assert u.accounting_status == "OK" and u.total_tokens == 14


def test_provider_inconsistent_total_preserved_but_invalid():
    u = extract_provider_usage({"usage":{"prompt_tokens":10,"completion_tokens":4,"total_tokens":999}}, attempt_id="v2", retry_index=0)
    assert u.accounting_status == INVALID and u.total_tokens == 999


@pytest.mark.parametrize("usage", [
    {"prompt_tokens":10,"completion_tokens":4},
    {"prompt_tokens":-1,"completion_tokens":4,"total_tokens":3},
    {"prompt_tokens":10.0,"completion_tokens":4,"total_tokens":14},
    {"prompt_tokens":True,"completion_tokens":4,"total_tokens":5},
])
def test_provider_malformed_accounting_is_invalid(usage):
    u = extract_provider_usage({"usage":usage}, attempt_id="bad", retry_index=0)
    assert u.accounting_status == INVALID


def test_missing_usage_after_possible_generation_is_invalid_without_estimate():
    u = extract_provider_usage({"choices":[{"message":{"content":"generated"}}]}, attempt_id="missing", retry_index=0, possibly_generated=True)
    assert u.accounting_status == INVALID
    assert (u.input_tokens, u.output_tokens, u.total_tokens) == (None, None, None)


def test_nested_audit_fields_preserve_provider_branches_without_changing_total():
    raw = {
        "prompt_tokens":20,
        "completion_tokens":5,
        "total_tokens":25,
        "prompt_tokens_details":{"cached_tokens":7,"other":1},
        "completion_tokens_details":{"reasoning_tokens":3,"other":2},
    }
    u = extract_provider_usage({"usage":raw}, attempt_id="nested", retry_index=0)
    assert u.raw_usage == raw
    assert u.cached_fields == {"prompt_tokens_details": raw["prompt_tokens_details"]}
    assert u.reasoning_fields == {"completion_tokens_details": raw["completion_tokens_details"]}
    assert u.total_tokens == 25 and u.accounting_status == "OK"
