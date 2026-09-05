from __future__ import annotations

import hashlib
import importlib
import json
import os
import sqlite3
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
from minisweagent.instrumentation.token_logger import INVALID, extract_provider_usage

fpmod = importlib.import_module("minisweagent.memory.fingerprint")


def mkstore(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "memory.sqlite")


def put(store: MemoryStore, *, task: str = "t", step: int = 1, content: str = "x", kind: str = "TOOL", **kw):
    return store.store(MemoryEvent(task_id=task, step_id=step, content=content, kind=kind, **kw))[0]


def state(step: int = 50000, task: str = "t", **kw) -> RetrievalState:
    return RetrievalState(task_id=task, current_step=step, **kw)


def candidate_ids(result) -> set[int]:
    return {x["memory_id"] for x in result.candidates}


def selected_ids(result) -> set[int]:
    return {x["memory_id"] for x in result.selected}


def bulk_current(store: MemoryStore, rows: list[tuple]):
    vals = []
    for step, content, command, outcome, mtype, verification, paths, fps in rows:
        content_fp = hashlib.sha256(content.encode("utf-8")).hexdigest()
        command_norm = _normalize_command(command)
        search_norm = _normalize_search_text(content, command, None)
        key = _scientific_key(
            content_fingerprint=content_fp,
            memory_type=mtype,
            verification_status=verification,
            outcome=outcome,
            command=command,
            file_paths=paths,
            file_fingerprints=fps,
        )
        vals.append((
            "t", step, mtype, content, None,
            json.dumps(paths, separators=(",", ":"), ensure_ascii=True),
            command, outcome, verification, 1, len(content.encode("utf-8")), content_fp,
            json.dumps(fps, sort_keys=True, separators=(",", ":"), ensure_ascii=True),
            command_norm, search_norm, key, None,
        ))
    with store.connect() as con:
        con.executemany(
            """INSERT INTO memories(task_id,step_id,memory_type,content,source_ref,file_paths,command,outcome,
               verification_status,importance,token_count,fingerprint,file_fingerprints,command_norm,search_norm,
               scientific_key,supersedes,invalidated_by)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)""",
            vals,
        )


def test_c01_exact_flood_preserves_scientifically_distinct_verification_and_target(tmp_path):
    s = mkstore(tmp_path)
    target = put(s, step=1, content="alpha beta unique target", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2)
    verified = put(s, step=2, content="alpha beta duplicate", memory_type="ERROR", verification_status="VERIFIED", outcome="FAILED", importance=2)
    bulk_current(s, [
        (100 + i, "alpha beta duplicate", None, "FAILED", "ERROR", "OBSERVED", [], [])
        for i in range(5000)
    ])
    r = retrieve("alpha beta", state(), 2048, db_path=s.db_path)
    ids = candidate_ids(r)
    assert target.memory_id in ids
    assert verified.memory_id in ids
    observed = [c for c in r.candidates if c["memory_id"] not in {target.memory_id, verified.memory_id}]
    assert observed, "OBSERVED scientific class disappeared behind exact grouping"


def test_c02_exact_duplicates_across_steps_group_without_erasing_unique_record(tmp_path):
    s = mkstore(tmp_path)
    target = put(s, step=1, content="grouping unique evidence", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2)
    bulk_current(s, [
        (10 + i, "grouping repeated evidence", None, None, "TOOL_RESULT", "OBSERVED", [], [])
        for i in range(600)
    ])
    r = retrieve("grouping evidence", state(), 2048, db_path=s.db_path)
    ids = candidate_ids(r)
    assert target.memory_id in ids
    repeated = [c for c in r.candidates if c["memory_id"] != target.memory_id]
    assert len(repeated) == 1, "exact duplicate source steps should group to one representative"


def test_c03_nfkc_command_collision_must_not_erase_shell_distinct_evidence(tmp_path):
    s = mkstore(tmp_path)
    # NBSP is not ordinary shell IFS space, but NFKC maps it to ASCII space.
    cmd_nbsp = "echo\u00a0x"
    cmd_space = "echo x"
    assert cmd_nbsp != cmd_space
    assert _normalize_command(cmd_nbsp) == _normalize_command(cmd_space)
    a = put(s, step=1, content="same command failure evidence", command=cmd_nbsp, outcome="FAILED", memory_type="FAILED_APPROACH", verification_status="OBSERVED", importance=2)
    b = put(s, step=2, content="same command failure evidence", command=cmd_space, outcome="FAILED", memory_type="FAILED_APPROACH", verification_status="OBSERVED", importance=2)
    r = retrieve("same command failure evidence", state(step=10), 2048, db_path=s.db_path)
    assert {a.memory_id, b.memory_id} <= candidate_ids(r), "NFKC collapsed shell-distinct commands into one scientific equivalence class"


def test_c04_internal_command_spacing_remains_semantically_distinct(tmp_path):
    s = mkstore(tmp_path)
    bad = put(s, step=1, content="old command spacing failure", command="echo  a", outcome="FAILED", memory_type="FAILED_APPROACH", verification_status="OBSERVED", importance=2)
    bulk_current(s, [(100+i, f"noise row {i}", None, None, "TOOL_RESULT", "OBSERVED", [], []) for i in range(300)])
    r = retrieve("unrelated recovery", state(failed_command_signature="echo a"), 2048, db_path=s.db_path)
    assert bad.memory_id not in candidate_ids(r), "normalization unsafely collapsed internal shell whitespace"


def _create_realistic_legacy_db(path: Path):
    con = sqlite3.connect(path)
    con.executescript("""
    CREATE TABLE memories (
      memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
      task_id TEXT NOT NULL, step_id INTEGER NOT NULL, memory_type TEXT NOT NULL, content TEXT NOT NULL,
      source_ref TEXT, file_paths TEXT NOT NULL DEFAULT '[]', command TEXT, outcome TEXT,
      verification_status TEXT NOT NULL, importance INTEGER NOT NULL DEFAULT 1, token_count INTEGER NOT NULL,
      fingerprint TEXT NOT NULL, file_fingerprints TEXT NOT NULL DEFAULT '[]', supersedes INTEGER, invalidated_by INTEGER
    );
    CREATE VIRTUAL TABLE memories_fts USING fts5(content,command,source_ref,task_id UNINDEXED,memory_id UNINDEXED,tokenize='unicode61');
    CREATE TRIGGER memories_ai AFTER INSERT ON memories BEGIN
      INSERT INTO memories_fts(rowid,content,command,source_ref,task_id,memory_id)
      VALUES(new.memory_id,new.content,coalesce(new.command,''),coalesce(new.source_ref,''),new.task_id,new.memory_id);
    END;
    """)
    content = "legacy migrated command evidence"
    fp = hashlib.sha256(content.encode()).hexdigest()
    con.execute("""INSERT INTO memories(task_id,step_id,memory_type,content,source_ref,file_paths,command,outcome,
      verification_status,importance,token_count,fingerprint,file_fingerprints,supersedes,invalidated_by)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)""",
      ("t",1,"FAILED_APPROACH",content,None,"[]","\tpytest legacy.py\n","FAILED","OBSERVED",1,len(content),fp,"[]",None))
    con.commit(); con.close()


def test_c05_legacy_schema_migration_is_idempotent_and_searchable_after_reopen(tmp_path):
    db = tmp_path / "legacy.sqlite"
    _create_realistic_legacy_db(db)
    s1 = MemoryStore(db)
    with s1.connect() as con:
        row1 = con.execute("SELECT command_norm,search_norm,scientific_key FROM memories").fetchone()
        n1 = con.execute("SELECT count(*) FROM memories_norm_fts").fetchone()[0]
    s2 = MemoryStore(db)
    with s2.connect() as con:
        row2 = con.execute("SELECT command_norm,search_norm,scientific_key FROM memories").fetchone()
        n2 = con.execute("SELECT count(*) FROM memories_norm_fts").fetchone()[0]
    assert tuple(row1) == tuple(row2)
    assert row2[0] == "pytest legacy.py" and len(row2[2]) == 64
    assert n1 == n2 == 1
    r = retrieve("unrelated", state(failed_command_signature="pytest legacy.py"), 2048, db_path=db)
    assert r.selected


def test_c06_malformed_legacy_json_fails_loudly_not_silently(tmp_path):
    s = mkstore(tmp_path)
    with s.connect() as con:
        content = "malformed legacy row"
        fp = hashlib.sha256(content.encode()).hexdigest()
        con.execute("""INSERT INTO memories(task_id,step_id,memory_type,content,source_ref,file_paths,command,outcome,
          verification_status,importance,token_count,fingerprint,file_fingerprints,command_norm,search_norm,scientific_key,supersedes,invalidated_by)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)""",
          ("t",1,"TOOL_RESULT",content,None,"not-json",None,None,"OBSERVED",1,len(content),fp,"[]","","","",None))
    with pytest.raises(json.JSONDecodeError):
        MemoryStore(s.db_path)


def test_c07_signature_numeric_suffix_not_prefix_match(tmp_path):
    s = mkstore(tmp_path)
    bad = put(s, step=1, content="failure ABC_10", returncode=1)
    r = retrieve("unrelated", state(error_signature="ABC_1"), 2048, db_path=s.db_path)
    assert bad.memory_id not in candidate_ids(r)


def test_c08_multitoken_signature_requires_contiguous_tokens(tmp_path):
    s = mkstore(tmp_path)
    bad = put(s, step=1, content="undefined noisy reference", returncode=1)
    good = put(s, step=2, content="undefined reference", returncode=1)
    r = retrieve("unrelated", state(step=10, error_signature="undefined reference"), 2048, db_path=s.db_path)
    ids = candidate_ids(r)
    assert good.memory_id in ids and bad.memory_id not in ids


def test_c09_signature_punctuation_token_boundary_is_deterministic(tmp_path):
    s = mkstore(tmp_path)
    rec = put(s, step=1, content="failure ERR-42", returncode=1)
    r = retrieve("unrelated", state(error_signature="ERR 42"), 2048, db_path=s.db_path)
    assert rec.memory_id in candidate_ids(r)


def test_c10_reordered_file_path_list_with_same_state_dedups(tmp_path):
    (tmp_path / "a").write_text("A"); (tmp_path / "b").write_text("B")
    s = mkstore(tmp_path)
    a = put(s, step=1, content="reordered file evidence", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2, file_paths=["a","b"], workspace=str(tmp_path))
    b = put(s, step=2, content="reordered file evidence", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2, file_paths=["b","a"], workspace=str(tmp_path))
    r = retrieve("reordered file evidence", state(step=10, workspace=str(tmp_path), file_paths=["a","b"]), 2048, db_path=s.db_path)
    present = candidate_ids(r) & {a.memory_id,b.memory_id}
    assert len(present) == 1


def test_c11_same_file_set_one_sha_changed_remains_distinct(tmp_path):
    (tmp_path / "a").write_text("A1"); (tmp_path / "b").write_text("B")
    s = mkstore(tmp_path)
    a = put(s, step=1, content="two-file evidence", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2, file_paths=["a","b"], workspace=str(tmp_path))
    (tmp_path / "a").write_text("A2")
    b = put(s, step=2, content="two-file evidence", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2, file_paths=["a","b"], workspace=str(tmp_path))
    r = retrieve("two-file evidence", state(step=10, workspace=str(tmp_path), file_paths=["a","b"]), 2048, db_path=s.db_path)
    assert {a.memory_id,b.memory_id} <= candidate_ids(r)


def test_c12_missing_vs_existing_file_state_remains_distinct(tmp_path):
    p = tmp_path / "state"; p.write_text("present")
    s = mkstore(tmp_path)
    a = put(s, step=1, content="missing-state evidence", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2, file_paths=["state"], workspace=str(tmp_path))
    p.unlink()
    b = put(s, step=2, content="missing-state evidence", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2, file_paths=["state"], workspace=str(tmp_path))
    r = retrieve("missing-state evidence", state(step=10, workspace=str(tmp_path), file_paths=["state"]), 2048, db_path=s.db_path)
    assert {a.memory_id,b.memory_id} <= candidate_ids(r)


def _mutate_first_read(monkeypatch, callback):
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


def test_c13_symlink_inside_outside_inside_aba_fails_closed(tmp_path, monkeypatch):
    a = tmp_path / "a"; a.write_text("same")
    outside = tmp_path.parent / (tmp_path.name + "-outside"); outside.write_text("same")
    link = tmp_path / "link"; link.symlink_to(a.name)
    def mutate():
        link.unlink(); link.symlink_to(outside); link.unlink(); link.symlink_to(a.name)
    fired = _mutate_first_read(monkeypatch, mutate)
    try:
        cur = fingerprint("link", tmp_path)
        assert fired() and cur.status != "OK"
    finally:
        outside.unlink(missing_ok=True)


def test_c14_regular_rename_recreate_same_size_restored_mtime_fails_closed(tmp_path, monkeypatch):
    p = tmp_path / "state"; p.write_text("AAAA")
    old_stat = p.stat(); moved = tmp_path / "moved"
    def mutate():
        p.rename(moved); p.write_text("BBBB"); os.utime(p, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
    fired = _mutate_first_read(monkeypatch, mutate)
    cur = fingerprint("state", tmp_path)
    assert fired() and cur.status != "OK"


def test_c15_symlink_regular_symlink_aba_fails_closed(tmp_path, monkeypatch):
    target = tmp_path / "target"; target.write_text("payload")
    link = tmp_path / "link"; link.symlink_to(target.name)
    def mutate():
        link.unlink(); link.write_text("payload"); link.unlink(); link.symlink_to(target.name)
    fired = _mutate_first_read(monkeypatch, mutate)
    cur = fingerprint("link", tmp_path)
    assert fired() and cur.status != "OK"


def test_c16_rapid_repeated_symlink_aba_has_zero_ok(tmp_path, monkeypatch):
    a = tmp_path / "a"; b = tmp_path / "b"; link = tmp_path / "link"
    a.write_text("same"); b.write_text("same"); link.symlink_to(a.name)
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
    for _ in range(50):
        if link.exists() or link.is_symlink(): link.unlink()
        link.symlink_to(a.name); pending = True
        ok += int(fingerprint("link", tmp_path).status == "OK")
    assert ok == 0


def test_c17_old_mixed_unicode_ascii_shadow_lookup_over_3000(tmp_path):
    s = mkstore(tmp_path)
    target = put(s, step=1, content="Straße_ID42")
    bulk_current(s, [(100+i, f"noise {i}", None, None, "TOOL_RESULT", "OBSERVED", [], []) for i in range(3200)])
    r = retrieve("STRASSE_id42", state(), 2048, db_path=s.db_path)
    assert target.memory_id in candidate_ids(r)
    meta = next(c for c in r.candidates if c["memory_id"] == target.memory_id)
    assert "normalized_local" in meta["sources"] or "local" in meta["sources"]


def test_c18_normalized_shadow_remains_task_local(tmp_path):
    s = mkstore(tmp_path)
    foreign = put(s, task="foreign", step=1, content="Straße_UNIQUE")
    local = put(s, task="t", step=2, content="different local record")
    r = retrieve("STRASSE_unique", state(step=10), 2048, db_path=s.db_path)
    assert foreign.memory_id not in candidate_ids(r)
    assert local.memory_id not in candidate_ids(r)


def test_c19_source_fairness_20_local_10_task_100_explicit(tmp_path):
    s = mkstore(tmp_path)
    for i in range(20):
        put(s, step=1+i, content=f"localsignal evidence {i}", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=1)
    for i in range(10):
        put(s, step=50+i, content=f"tasksignal context {i}", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=1)
    for i in range(100):
        put(s, step=100+i, content=f"E_FAIR explicit decoy {i}", returncode=1)
    r = retrieve("localsignal", state(task_text="tasksignal", error_signature="E_FAIR"), 2048, db_path=s.db_path)
    assert len(r.candidates) <= 40
    supplemental = [c for c in r.candidates if c["rank"] >= 10**6]
    assert len(supplemental) <= 10
    assert sum("local" in c["sources"] for c in r.candidates) >= 20
    assert any("error_signature" in c["sources"] for c in r.candidates)


def test_c20_relevant_explicit_failure_survives_full_ordinary_pool(tmp_path):
    s = mkstore(tmp_path)
    explicit = put(s, step=1, content="rare E_EXPLICIT marker", returncode=1)
    for i in range(20): put(s, step=10+i, content=f"localword evidence {i}")
    for i in range(10): put(s, step=50+i, content=f"taskword evidence {i}")
    r = retrieve("localword", state(task_text="taskword", error_signature="E_EXPLICIT"), 2048, db_path=s.db_path)
    assert explicit.memory_id in candidate_ids(r)


def test_c21_verified_numeric_correction_still_not_destroyed(tmp_path):
    s = mkstore(tmp_path)
    old = put(s, step=1, content="timeout 30", kind="ASSISTANT")
    new = put(s, step=2, content="timeout 60", memory_type="TEST_RESULT", verification_status="VERIFIED", importance=2)
    r = retrieve("timeout", state(step=10), 2048, db_path=s.db_path)
    assert new.memory_id in candidate_ids(r)
    assert old.memory_id not in selected_ids(r)


def test_c22_token_accounting_spotcheck_still_fails_closed():
    good = extract_provider_usage({"usage":{"prompt_tokens":10,"completion_tokens":4,"total_tokens":14}}, attempt_id="g", retry_index=0)
    bad = extract_provider_usage({"usage":{"prompt_tokens":10,"completion_tokens":4,"total_tokens":999}}, attempt_id="b", retry_index=0)
    missing = extract_provider_usage({"choices":[{"message":{"content":"x"}}]}, attempt_id="m", retry_index=0)
    assert good.accounting_status == "OK"
    assert bad.accounting_status == INVALID and bad.total_tokens == 999
    assert missing.accounting_status == INVALID and missing.total_tokens is None
