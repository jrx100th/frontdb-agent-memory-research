from __future__ import annotations

import hashlib
import json
import subprocess
import unicodedata
from pathlib import Path

import pytest

from minisweagent.memory.retrieve import RetrievalState, retrieve
from minisweagent.memory.store import (
    MemoryEvent,
    MemoryStore,
    _command_lookup_key,
    _normalize_search_text,
    _raw_command_sha256,
    _scientific_key,
)


def bash(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", command],
        text=True,
        capture_output=True,
        check=False,
    )


def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "memory.sqlite")


def put(s: MemoryStore, command: str, step: int, *, task: str = "t", content: str = "focused command evidence"):
    return s.store(
        MemoryEvent(
            task_id=task,
            step_id=step,
            content=content,
            kind="TOOL",
            command=command,
            outcome="FAILED",
            memory_type="FAILED_APPROACH",
            verification_status="OBSERVED",
            importance=2,
        )
    )[0]


def sci(command: str | None, content_fp: str = "0" * 64) -> str:
    return _scientific_key(
        content_fingerprint=content_fp,
        memory_type="FAILED_APPROACH",
        verification_status="OBSERVED",
        outcome="FAILED",
        command=command,
        file_paths=[],
        file_fingerprints=[],
    )


def cids(result) -> set[int]:
    return {x["memory_id"] for x in result.candidates}


def sids(result) -> set[int]:
    return {x["memory_id"] for x in result.selected}


def lookup(s: MemoryStore, command: str, *, task: str = "t", step: int = 5000):
    return retrieve(
        "unrelated recovery planning",
        RetrievalState(task_id=task, current_step=step, failed_command_signature=command),
        2048,
        db_path=s.db_path,
    )


def assert_raw_distinct(a: str, b: str) -> None:
    assert a.encode("utf-8") != b.encode("utf-8")
    assert _raw_command_sha256(a) != _raw_command_sha256(b)
    assert sci(a) != sci(b)


def legacy_nfkc_key(value: str | None) -> str:
    if not value:
        return ""
    return unicodedata.normalize("NFKC", value).strip()


def legacy_scientific(command: str | None, content_fp: str) -> str:
    payload = {
        "content_fingerprint": content_fp,
        "memory_type": "FAILED_APPROACH",
        "verification_status": "OBSERVED",
        "outcome": "failed",
        "command_norm": legacy_nfkc_key(command),
        "file_paths": (),
        "file_fingerprints": (),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def force_previous_derived_rule(s: MemoryStore) -> None:
    with s.connect() as con:
        rows = con.execute("SELECT memory_id,command,fingerprint FROM memories ORDER BY memory_id").fetchall()
        for row in rows:
            con.execute(
                "UPDATE memories SET command_norm=?, scientific_key=? WHERE memory_id=?",
                (legacy_nfkc_key(row["command"]), legacy_scientific(row["command"], row["fingerprint"]), row["memory_id"]),
            )


def test_f01_c03_exact_shell_behavior_and_end_to_end_noncollapse(tmp_path):
    ascii_cmd = "echo x"
    nbsp_cmd = "echo\u00a0x"
    a_run, b_run = bash(ascii_cmd), bash(nbsp_cmd)
    assert a_run.returncode == 0
    assert b_run.returncode != 0
    assert _command_lookup_key(ascii_cmd) != _command_lookup_key(nbsp_cmd)
    assert_raw_distinct(ascii_cmd, nbsp_cmd)
    s = store(tmp_path)
    a = put(s, ascii_cmd, 1)
    b = put(s, nbsp_cmd, 2)
    r = retrieve("focused command evidence", RetrievalState(task_id="t", current_step=10), 2048, db_path=s.db_path)
    assert {a.memory_id, b.memory_id} <= cids(r)


@pytest.mark.parametrize("ws", ["\u00a0", "\u3000", "\u202f", "\u2003", "\u2007"])
def test_f02_unicode_boundary_whitespace_is_not_stripped(ws):
    canonical = "pytest x"
    variant = ws + canonical + ws
    assert _command_lookup_key(variant) == variant
    assert _command_lookup_key(variant) != _command_lookup_key(canonical)
    assert_raw_distinct(canonical, variant)


def test_f03_unicode_normalization_forms_remain_scientifically_distinct():
    pre = "printf '%s' café"
    decomp = "printf '%s' cafe\u0301"
    assert unicodedata.normalize("NFC", decomp) == pre
    assert _command_lookup_key(pre) != _command_lookup_key(decomp)
    assert_raw_distinct(pre, decomp)
    assert bash(pre).stdout != bash(decomp).stdout


def test_f04_zero_width_codepoint_is_preserved():
    normal = "echo x"
    zwsp = "echo\u200bx"
    assert _command_lookup_key(normal) != _command_lookup_key(zwsp)
    assert_raw_distinct(normal, zwsp)
    assert bash(normal).returncode != bash(zwsp).returncode


def test_f05_internal_newline_is_not_folded_to_space():
    with_newline = "printf x\necho y"
    with_space = "printf x echo y"
    assert _command_lookup_key(with_newline) != _command_lookup_key(with_space)
    assert_raw_distinct(with_newline, with_space)
    assert bash(with_newline).stdout != bash(with_space).stdout


@pytest.mark.parametrize("edge", ["\r", "\v", "\f"])
def test_f06_nonapproved_ascii_boundary_controls_remain_distinct(edge):
    canonical = "pytest x"
    variant = edge + canonical + edge
    assert _command_lookup_key(variant) == variant
    assert _command_lookup_key(variant) != canonical
    assert_raw_distinct(canonical, variant)


def test_f07_shell_significant_trailing_space_collision_keeps_both_records(tmp_path):
    # Trimming the final ASCII space intentionally makes these lookup-collide,
    # even though the space is escaped and Bash behavior differs. Raw identity
    # must therefore be the safety barrier against destructive scientific dedup.
    escaped_space = "printf '<%s>' x\\ "
    bare_backslash = "printf '<%s>' x\\"
    assert bash(escaped_space).stdout != bash(bare_backslash).stdout
    assert _command_lookup_key(escaped_space) == _command_lookup_key(bare_backslash)
    assert_raw_distinct(escaped_space, bare_backslash)
    s = store(tmp_path)
    a = put(s, escaped_space, 1, content="lookup collision evidence")
    b = put(s, bare_backslash, 2, content="lookup collision evidence")
    r = lookup(s, bare_backslash, step=10)
    assert {a.memory_id, b.memory_id} <= cids(r)
    assert {a.memory_id, b.memory_id} <= sids(r)


def test_f08_many_allowed_boundary_forms_share_lookup_but_not_scientific_identity(tmp_path):
    variants = ["pytest x", "  pytest x", "pytest x\t", "\npytest x\n", "\t pytest x \n"]
    assert len({_command_lookup_key(v) for v in variants}) == 1
    assert len({_raw_command_sha256(v) for v in variants}) == len(variants)
    assert len({sci(v) for v in variants}) == len(variants)
    s = store(tmp_path)
    recs = [put(s, v, i + 1, content="boundary collision family") for i, v in enumerate(variants)]
    r = lookup(s, "pytest x", step=20)
    ids = {x.memory_id for x in recs}
    assert ids <= cids(r)
    assert ids <= sids(r)


def test_f09_single_quote_double_quote_same_output_stays_raw_distinct(tmp_path):
    single = "printf '%s' 'x'"
    double = 'printf \'%s\' "x"'
    assert bash(single).stdout == bash(double).stdout == "x"
    assert _command_lookup_key(single) != _command_lookup_key(double)
    assert_raw_distinct(single, double)
    s = store(tmp_path)
    a = put(s, single, 1, content="quote evidence")
    b = put(s, double, 2, content="quote evidence")
    r = retrieve("quote evidence", RetrievalState(task_id="t", current_step=10), 2048, db_path=s.db_path)
    assert {a.memory_id, b.memory_id} <= cids(r)


def test_f10_shell_metacharacter_difference_stays_raw_distinct():
    a = "printf x; printf y"
    b = "printf x\\; printf y"
    assert bash(a).stdout != bash(b).stdout
    assert _command_lookup_key(a) != _command_lookup_key(b)
    assert_raw_distinct(a, b)


def test_f11_previous_nfkc_collision_migrates_and_reopens_idempotently(tmp_path):
    s = store(tmp_path)
    a = put(s, "echo\u00a0x", 1, content="legacy migrated evidence")
    b = put(s, "echo x", 2, content="legacy migrated evidence")
    force_previous_derived_rule(s)
    with s.connect() as con:
        stale = con.execute("SELECT command_norm,scientific_key FROM memories ORDER BY memory_id").fetchall()
    assert stale[0][0] == stale[1][0] == "echo x"
    assert stale[0][1] == stale[1][1]

    m1 = MemoryStore(s.db_path)
    with m1.connect() as con:
        first = [tuple(row) for row in con.execute("SELECT command_norm,scientific_key FROM memories ORDER BY memory_id")]
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        indexes = {row[1] for row in con.execute("PRAGMA index_list(memories)")}
    assert first[0][0] == "echo\u00a0x"
    assert first[1][0] == "echo x"
    assert first[0][1] != first[1][1]
    assert "idx_memories_task_command_norm" in indexes
    assert "idx_memories_task_scientific_key" in indexes

    m2 = MemoryStore(s.db_path)
    with m2.connect() as con:
        second = [tuple(row) for row in con.execute("SELECT command_norm,scientific_key FROM memories ORDER BY memory_id")]
    assert first == second
    r_ascii = lookup(m2, "echo x", step=20)
    assert b.memory_id in cids(r_ascii)
    assert a.memory_id not in cids(r_ascii)


def test_f12_migration_preserves_lookup_collision_but_separates_scientific_keys(tmp_path):
    s = store(tmp_path)
    canonical = put(s, "pytest x", 1, content="migration collision evidence")
    padded = put(s, " \tpytest x\n", 2, content="migration collision evidence")
    force_previous_derived_rule(s)
    migrated = MemoryStore(s.db_path)
    with migrated.connect() as con:
        rows = con.execute("SELECT command_norm,scientific_key FROM memories ORDER BY memory_id").fetchall()
    assert rows[0][0] == rows[1][0] == "pytest x"
    assert rows[0][1] != rows[1][1]
    r = lookup(migrated, "pytest x", step=20)
    assert {canonical.memory_id, padded.memory_id} <= cids(r)


def test_f13_deep_indexed_lookup_after_migration_uses_new_key(tmp_path):
    s = store(tmp_path)
    target = put(s, " \tpytest deep_case.py\n", 1, content="deep focused target")
    # More than the recent supplemental window; use ordinary store semantics.
    for i in range(260):
        s.store(MemoryEvent(task_id="t", step_id=100 + i, content=f"noise {i}", kind="TOOL"))
    force_previous_derived_rule(s)
    migrated = MemoryStore(s.db_path)
    r = lookup(migrated, "pytest deep_case.py", step=1000)
    assert target.memory_id in cids(r)
    assert target.memory_id in sids(r)


def test_f14_failed_command_lookup_remains_task_local(tmp_path):
    s = store(tmp_path)
    local = put(s, "pytest task.py", 1, task="t", content="local command failure")
    foreign = put(s, "pytest task.py", 2, task="other", content="foreign command failure")
    r = lookup(s, "pytest task.py", task="t", step=20)
    assert local.memory_id in cids(r)
    assert foreign.memory_id not in cids(r)


def test_f15_general_unicode_lexical_normalization_remains_separate_from_command_lookup():
    assert _normalize_search_text("Straße") == "strasse"
    assert _normalize_search_text("ｅｃｈｏ") == "echo"
    assert _command_lookup_key("ｅｃｈｏ") == "ｅｃｈｏ"
    assert _command_lookup_key("echo") == "echo"
    assert _command_lookup_key("ｅｃｈｏ") != _command_lookup_key("echo")
