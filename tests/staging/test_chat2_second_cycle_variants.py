from __future__ import annotations

import hashlib
import importlib
import json
import os
import sqlite3
import time
from pathlib import Path

import pytest

from minisweagent.memory.store import (
    MemoryEvent,
    MemoryStore,
    _normalize_command,
    _normalize_search_text,
    _scientific_key,
)
from minisweagent.memory.retrieve import RetrievalState, retrieve
from minisweagent.memory.fingerprint import fingerprint

fpmod = importlib.import_module("minisweagent.memory.fingerprint")


def mkstore(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "memory.sqlite")


def put(store: MemoryStore, *, task: str = "t", step: int = 1, content: str = "x", kind: str = "TOOL", **kw):
    return store.store(MemoryEvent(task_id=task, step_id=step, content=content, kind=kind, **kw))[0]


def state(step: int = 50000, **kw) -> RetrievalState:
    return RetrievalState(task_id="t", current_step=step, **kw)


def ids(result) -> list[int]:
    return [x["memory_id"] for x in result.selected]


def bulk_production_rows(
    store: MemoryStore,
    rows: list[tuple[int, str, str | None, str | None, str, str, list[str], list[dict]]],
) -> None:
    values = []
    for step, content, command, outcome, mtype, verification, paths, fps in rows:
        fp = hashlib.sha256(content.encode("utf-8")).hexdigest()
        command_norm = _normalize_command(command)
        search_norm = _normalize_search_text(content, command, None)
        key = _scientific_key(
            content_fingerprint=fp,
            memory_type=mtype,
            verification_status=verification,
            outcome=outcome,
            command=command,
            file_paths=paths,
            file_fingerprints=fps,
        )
        values.append((
            "t", step, mtype, content, None,
            json.dumps(paths, separators=(",", ":"), ensure_ascii=True),
            command, outcome, verification, 1, len(content.encode("utf-8")), fp,
            json.dumps(fps, sort_keys=True, separators=(",", ":"), ensure_ascii=True),
            command_norm, search_norm, key, None,
        ))
    with store.connect() as con:
        con.executemany(
            """INSERT INTO memories(task_id,step_id,memory_type,content,source_ref,file_paths,command,outcome,
               verification_status,importance,token_count,fingerprint,file_fingerprints,command_norm,search_norm,
               scientific_key,supersedes,invalidated_by)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)""",
            values,
        )


def _db_size(store: MemoryStore) -> int:
    return os.path.getsize(store.db_path)


def test_v01_exact_duplicate_flood_10000_and_work_observation(tmp_path, capsys):
    s = mkstore(tmp_path)
    target = put(s, step=1, content="alpha beta unique target", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2)
    bulk_production_rows(s, [
        (100 + i, "alpha beta duplicate", None, "FAILED", "ERROR", "OBSERVED", [], [])
        for i in range(10_000)
    ])
    with s.connect() as con:
        matching = con.execute("SELECT count(*) FROM memories_fts WHERE memories_fts MATCH ?", ('\"alpha\" OR \"beta\"',)).fetchone()[0]
        total = con.execute("SELECT count(*) FROM memories").fetchone()[0]
    started = time.perf_counter()
    r = retrieve("alpha beta", state(), 2048, db_path=s.db_path)
    elapsed = time.perf_counter() - started
    print(f"V01 matching_rows={matching} db_rows={total} candidates={len(r.candidates)} runtime_s={elapsed:.6f} db_bytes={_db_size(s)}")
    assert target.memory_id in ids(r)
    assert matching == 10_001


def test_v02_exact_duplicate_flood_over_10000(tmp_path):
    s = mkstore(tmp_path)
    target = put(s, step=1, content="omega theta distinct useful", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2)
    bulk_production_rows(s, [
        (100 + i, "omega theta repeated", None, "FAILED", "ERROR", "OBSERVED", [], [])
        for i in range(12_345)
    ])
    assert target.memory_id in ids(retrieve("omega theta", state(), 2048, db_path=s.db_path))


def test_v03_near_duplicate_punctuation_flood(tmp_path):
    s = mkstore(tmp_path)
    target = put(s, step=1, content="near flood useful target", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2)
    punct = "!@#$%^&*()-=+[]{};:,./?"
    rows = []
    for i in range(600):
        suffix = "".join(punct[(i >> bit) % len(punct)] for bit in range(1, 7))
        rows.append((100 + i, f"near flood duplicate {suffix}", None, "FAILED", "ERROR", "OBSERVED", [], []))
    bulk_production_rows(s, rows)
    assert target.memory_id in ids(retrieve("near flood", state(), 2048, db_path=s.db_path))


def test_v04_mixed_explicit_flood_keeps_ordinary_lexical_candidate(tmp_path):
    s = mkstore(tmp_path)
    target = put(s, step=1, content="ordinary exact lexical winner", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2)
    bulk_production_rows(s, [
        (100 + i, f"E_MIX explicit decoy {i}", None, "FAILED", "ERROR", "OBSERVED", [], [])
        for i in range(100)
    ])
    r = retrieve("ordinary exact lexical winner", state(error_signature="E_MIX"), 2048, db_path=s.db_path)
    assert target.memory_id in ids(r)
    supplemental_only = [c for c in r.candidates if c["rank"] >= 10**6]
    assert len(supplemental_only) <= 10
    assert len(r.candidates) <= 40


@pytest.mark.parametrize("stored", [" pytest tests/a.py ", "\tpytest tests/a.py\n", "pytest tests/a.py"])
def test_v05_command_whitespace_variants_deep_recall(tmp_path, stored):
    s = mkstore(tmp_path)
    target = put(s, step=1, content="old command failure", command=stored, outcome="FAILED", memory_type="FAILED_APPROACH", verification_status="OBSERVED", importance=2)
    bulk_production_rows(s, [(100+i, f"noise {i}", None, None, "TOOL_RESULT", "OBSERVED", [], []) for i in range(1000)])
    r = retrieve("unrelated", state(failed_command_signature="pytest tests/a.py"), 2048, db_path=s.db_path)
    assert target.memory_id in ids(r)


def test_v06_derived_field_backfill_for_legacy_like_row(tmp_path):
    s = mkstore(tmp_path)
    with s.connect() as con:
        content = "legacy strasse command"
        fp = hashlib.sha256(content.encode()).hexdigest()
        con.execute(
            """INSERT INTO memories(task_id,step_id,memory_type,content,source_ref,file_paths,command,outcome,
               verification_status,importance,token_count,fingerprint,file_fingerprints,command_norm,search_norm,
               scientific_key,supersedes,invalidated_by)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)""",
            ("t",1,"FAILED_APPROACH",content,None,"[]"," pytest tests/a.py ","FAILED","OBSERVED",1,len(content),fp,"[]","","","",None),
        )
    s2 = MemoryStore(s.db_path)
    with s2.connect() as con:
        row = con.execute("SELECT command_norm,search_norm,scientific_key FROM memories WHERE step_id=1").fetchone()
    assert row["command_norm"] == "pytest tests/a.py"
    assert row["search_norm"]
    assert len(row["scientific_key"]) == 64


@pytest.mark.parametrize("record, query", [("ABC_10", "ABC_1"), ("E_SIG_EXTRA", "E_SIG"), ("ERR42X", "ERR42")])
def test_v07_similar_error_signatures_are_not_exact(record, query, tmp_path):
    s = mkstore(tmp_path)
    bad = put(s, step=1, content=f"failure {record}", returncode=1)
    r = retrieve("unrelated", state(error_signature=query), 2048, db_path=s.db_path)
    assert bad.memory_id not in ids(r)


def test_v08_exact_multitoken_error_signature_matches(tmp_path):
    s = mkstore(tmp_path)
    rec = put(s, step=1, content="build failed undefined reference widget_init", returncode=1)
    r = retrieve("unrelated", state(error_signature="undefined reference"), 2048, db_path=s.db_path)
    assert rec.memory_id in ids(r)


def test_v09_same_text_same_file_state_still_dedups(tmp_path):
    p = tmp_path / "a.txt"; p.write_text("same", encoding="utf-8")
    s = mkstore(tmp_path)
    a = put(s, step=1, content="same file evidence", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2, file_paths=["a.txt"], workspace=str(tmp_path))
    b = put(s, step=2, content="same file evidence", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2, file_paths=["a.txt"], workspace=str(tmp_path))
    got = ids(retrieve("same file evidence", state(step=10, workspace=str(tmp_path), file_paths=["a.txt"]), 2048, db_path=s.db_path))
    assert len([mid for mid in got if mid in {a.memory_id, b.memory_id}]) == 1


def test_v10_same_text_changed_sha_same_path_remains_distinct(tmp_path):
    p = tmp_path / "a.txt"; p.write_text("v1", encoding="utf-8")
    s = mkstore(tmp_path)
    a = put(s, step=1, content="same file evidence", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2, file_paths=["a.txt"], workspace=str(tmp_path))
    p.write_text("v2", encoding="utf-8")
    b = put(s, step=2, content="same file evidence", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2, file_paths=["a.txt"], workspace=str(tmp_path))
    got = ids(retrieve("same file evidence", state(step=10, workspace=str(tmp_path), file_paths=["a.txt"]), 2048, db_path=s.db_path))
    assert a.memory_id in got and b.memory_id in got


def test_v11_multiple_file_fingerprint_sets_remain_distinct(tmp_path):
    for name, value in [("a","A"),("b","B"),("c","C")]:
        (tmp_path / name).write_text(value, encoding="utf-8")
    s = mkstore(tmp_path)
    a = put(s, step=1, content="multi file state", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2, file_paths=["a","b"], workspace=str(tmp_path))
    b = put(s, step=2, content="multi file state", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2, file_paths=["a","c"], workspace=str(tmp_path))
    got = ids(retrieve("multi file state", state(step=10, workspace=str(tmp_path), file_paths=["a","b","c"]), 2048, db_path=s.db_path))
    assert a.memory_id in got and b.memory_id in got


def test_v12_repeated_real_symlink_aba_never_ok(tmp_path, monkeypatch, capsys):
    a = tmp_path / "a"; b = tmp_path / "b"; link = tmp_path / "link"
    a.write_text("same-bytes", encoding="utf-8"); b.write_text("same-bytes", encoding="utf-8"); link.symlink_to(a.name)
    original = fpmod.os.read
    pending = False
    def read(fd, n):
        nonlocal pending
        block = original(fd, n)
        if block and pending:
            pending = False
            link.unlink(); link.symlink_to(b.name); link.unlink(); link.symlink_to(a.name)
        return block
    monkeypatch.setattr(fpmod.os, "read", read)
    ok = 0
    runs = 30
    for _ in range(runs):
        if link.is_symlink():
            link.unlink()
        link.symlink_to(a.name)
        pending = True
        cur = fingerprint("link", tmp_path)
        ok += int(cur.status == "OK")
    print(f"V12 ABA_runs={runs} fresh_capable_OK={ok}")
    assert ok == 0


def test_v13_old_strasse_over_1000_uses_normalized_shadow(tmp_path):
    s = mkstore(tmp_path)
    target = put(s, step=1, content="straße")
    bulk_production_rows(s, [(100+i, f"noise {i}", None, None, "TOOL_RESULT", "OBSERVED", [], []) for i in range(1200)])
    r = retrieve("STRASSE", state(), 2048, db_path=s.db_path)
    assert target.memory_id in ids(r)
    meta = next(c for c in r.candidates if c["memory_id"] == target.memory_id)
    assert "normalized_local" in meta["sources"]


def test_v14_old_greek_final_sigma_over_3000(tmp_path):
    s = mkstore(tmp_path)
    target = put(s, step=1, content="ΟΣ")
    bulk_production_rows(s, [(100+i, f"noise {i}", None, None, "TOOL_RESULT", "OBSERVED", [], []) for i in range(3100)])
    assert target.memory_id in ids(retrieve("ος", state(), 2048, db_path=s.db_path))


def test_v15_old_combining_unicode_over_3000(tmp_path):
    s = mkstore(tmp_path)
    target = put(s, step=1, content="café")
    bulk_production_rows(s, [(100+i, f"noise {i}", None, None, "TOOL_RESULT", "OBSERVED", [], []) for i in range(3100)])
    assert target.memory_id in ids(retrieve("CAFE\u0301", state(), 2048, db_path=s.db_path))


def test_v16_normalized_shadow_false_positive_control(tmp_path):
    s = mkstore(tmp_path)
    bad = put(s, step=1, content="strassex")
    assert bad.memory_id not in ids(retrieve("STRASSE", state(step=10), 2048, db_path=s.db_path))


def test_v17_deep_failed_command_work_observation(tmp_path, capsys):
    s = mkstore(tmp_path)
    target = put(s, step=1, content="deep command failure", command=" pytest deep.py ", outcome="FAILED", memory_type="FAILED_APPROACH", verification_status="OBSERVED", importance=2)
    bulk_production_rows(s, [(100+i, f"noise row {i}", None, None, "TOOL_RESULT", "OBSERVED", [], []) for i in range(3200)])
    with s.connect() as con:
        total = con.execute("SELECT count(*) FROM memories").fetchone()[0]
        matches = con.execute("SELECT count(*) FROM memories WHERE task_id='t' AND command_norm=?", ("pytest deep.py",)).fetchone()[0]
    started = time.perf_counter()
    r = retrieve("unrelated", state(failed_command_signature="pytest deep.py"), 2048, db_path=s.db_path)
    elapsed = time.perf_counter() - started
    print(f"V17 db_rows={total} command_index_matches={matches} candidates={len(r.candidates)} runtime_s={elapsed:.6f} db_bytes={_db_size(s)}")
    assert target.memory_id in ids(r)
    assert matches == 1
