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
    _normalize_command,
    _normalize_search_text,
    _raw_command_sha256,
    _scientific_key,
)


def mkstore(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "memory.sqlite")


def put(store: MemoryStore, *, step: int, command: str, content: str = "same command failure evidence"):
    return store.store(
        MemoryEvent(
            task_id="t",
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


def candidate_ids(result) -> set[int]:
    return {x["memory_id"] for x in result.candidates}


def selected_ids(result) -> set[int]:
    return {x["memory_id"] for x in result.selected}


def run_bash(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", command],
        text=True,
        capture_output=True,
        check=False,
    )


def scientific_key(command: str | None) -> str:
    return _scientific_key(
        content_fingerprint="0" * 64,
        memory_type="FAILED_APPROACH",
        verification_status="OBSERVED",
        outcome="FAILED",
        command=command,
        file_paths=[],
        file_fingerprints=[],
    )


def assert_raw_identity_distinct(a: str, b: str) -> None:
    assert a != b
    assert _raw_command_sha256(a) != _raw_command_sha256(b)
    assert scientific_key(a) != scientific_key(b)


def legacy_nfkc_command(value: str | None) -> str:
    if not value:
        return ""
    return unicodedata.normalize("NFKC", value).strip()


def legacy_scientific_key(command: str | None, content_fingerprint: str) -> str:
    payload = {
        "content_fingerprint": content_fingerprint,
        "memory_type": "FAILED_APPROACH",
        "verification_status": "OBSERVED",
        "outcome": "failed",
        "command_norm": legacy_nfkc_command(command),
        "file_paths": (),
        "file_fingerprints": (),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def test_c03_ascii_space_and_nbsp_are_distinct_scientific_command_identity(tmp_path):
    cmd_space = "echo x"
    cmd_nbsp = "echo\u00a0x"

    normal = run_bash(cmd_space)
    nbsp = run_bash(cmd_nbsp)
    assert normal.returncode == 0
    assert nbsp.returncode != normal.returncode

    assert _normalize_command(cmd_space) != _normalize_command(cmd_nbsp)
    assert_raw_identity_distinct(cmd_space, cmd_nbsp)

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


def test_ascii_space_vs_ideographic_space_remain_distinct():
    ascii_cmd = "echo x"
    ideographic = "echo\u3000x"
    assert run_bash(ascii_cmd).returncode == 0
    assert run_bash(ideographic).returncode != 0
    assert _normalize_command(ascii_cmd) != _normalize_command(ideographic)
    assert_raw_identity_distinct(ascii_cmd, ideographic)


def test_ascii_letters_vs_fullwidth_letters_remain_distinct():
    ascii_cmd = "echo x"
    fullwidth = "ｅｃｈｏ x"
    assert run_bash(ascii_cmd).returncode == 0
    assert run_bash(fullwidth).returncode != 0
    assert _normalize_command(ascii_cmd) != _normalize_command(fullwidth)
    assert_raw_identity_distinct(ascii_cmd, fullwidth)


def test_ascii_punctuation_vs_fullwidth_punctuation_remain_distinct():
    ascii_cmd = "printf ';'"
    fullwidth = "printf '；'"
    a = run_bash(ascii_cmd)
    b = run_bash(fullwidth)
    assert a.returncode == b.returncode == 0
    assert a.stdout != b.stdout
    assert _normalize_command(ascii_cmd) != _normalize_command(fullwidth)
    assert_raw_identity_distinct(ascii_cmd, fullwidth)


def test_nfkc_ligature_compatibility_character_remains_distinct():
    ascii_cmd = "printf '%s' fi"
    ligature_cmd = "printf '%s' ﬁ"
    a = run_bash(ascii_cmd)
    b = run_bash(ligature_cmd)
    assert a.returncode == b.returncode == 0
    assert a.stdout != b.stdout
    assert unicodedata.normalize("NFKC", ligature_cmd) == ascii_cmd
    assert _normalize_command(ascii_cmd) != _normalize_command(ligature_cmd)
    assert_raw_identity_distinct(ascii_cmd, ligature_cmd)


def test_internal_single_vs_double_ascii_space_preserves_raw_identity():
    single = "echo a"
    double = "echo  a"
    assert run_bash(single).stdout == run_bash(double).stdout
    assert _normalize_command(single) != _normalize_command(double)
    assert_raw_identity_distinct(single, double)


def test_internal_tab_vs_space_preserves_raw_identity():
    space = "echo X"
    tab = "echo\tX"
    assert run_bash(space).stdout == run_bash(tab).stdout
    assert _normalize_command(space) != _normalize_command(tab)
    assert_raw_identity_distinct(space, tab)


def test_quoted_internal_whitespace_remains_distinct():
    single = 'printf "%s" "a b"'
    double = 'printf "%s" "a  b"'
    assert run_bash(single).stdout != run_bash(double).stdout
    assert _normalize_command(single) != _normalize_command(double)
    assert_raw_identity_distinct(single, double)


def test_quoted_vs_unquoted_command_remains_distinct():
    quoted = 'echo "a b"'
    unquoted = "echo a b"
    assert run_bash(quoted).stdout == run_bash(unquoted).stdout
    assert _normalize_command(quoted) != _normalize_command(unquoted)
    assert_raw_identity_distinct(quoted, unquoted)


def test_leading_trailing_ascii_spaces_are_lookup_equivalent_but_raw_distinct():
    canonical = "echo x"
    boundary = "  echo x   "
    assert run_bash(canonical).stdout == run_bash(boundary).stdout
    assert _normalize_command(canonical) == _normalize_command(boundary)
    assert_raw_identity_distinct(canonical, boundary)


def test_leading_trailing_ascii_tabs_are_lookup_equivalent_but_raw_distinct():
    canonical = "echo x"
    boundary = "\t\techo x\t"
    assert run_bash(canonical).stdout == run_bash(boundary).stdout
    assert _normalize_command(canonical) == _normalize_command(boundary)
    assert_raw_identity_distinct(canonical, boundary)


def test_terminal_ascii_newline_is_lookup_equivalent_but_raw_distinct():
    canonical = "echo x"
    boundary = "echo x\n"
    assert run_bash(canonical).stdout == run_bash(boundary).stdout
    assert _normalize_command(canonical) == _normalize_command(boundary)
    assert_raw_identity_distinct(canonical, boundary)


@pytest.mark.parametrize("variant", ["echo\u00a0x", "echo\u3000x"])
def test_failed_command_lookup_does_not_false_match_unicode_space_variants(tmp_path, variant):
    s = mkstore(tmp_path)
    rec = put(s, step=1, command=variant, content="unicode command only evidence")
    r = retrieve(
        "unrelated recovery planning",
        RetrievalState(task_id="t", current_step=1000, failed_command_signature="echo x"),
        2048,
        db_path=s.db_path,
    )
    assert rec.memory_id not in candidate_ids(r)


def test_failed_command_lookup_preserves_intended_ascii_boundary_noise(tmp_path):
    s = mkstore(tmp_path)
    rec = put(s, step=1, command=" \tpytest tests/a.py\t\n", content="deep boundary command evidence")
    r = retrieve(
        "unrelated recovery planning",
        RetrievalState(task_id="t", current_step=1000, failed_command_signature="pytest tests/a.py"),
        2048,
        db_path=s.db_path,
    )
    assert rec.memory_id in candidate_ids(r)
    assert rec.memory_id in selected_ids(r)


def _force_legacy_nfkc_derived_values(store: MemoryStore) -> tuple[tuple[str, str], ...]:
    with store.connect() as con:
        rows = con.execute(
            "SELECT memory_id,command,fingerprint FROM memories ORDER BY memory_id"
        ).fetchall()
        for row in rows:
            con.execute(
                "UPDATE memories SET command_norm=?, scientific_key=? WHERE memory_id=?",
                (
                    legacy_nfkc_command(row["command"]),
                    legacy_scientific_key(row["command"], row["fingerprint"]),
                    row["memory_id"],
                ),
            )
        return tuple(
            (row["command_norm"], row["scientific_key"])
            for row in con.execute(
                "SELECT command_norm,scientific_key FROM memories ORDER BY memory_id"
            )
        )


def test_old_nfkc_derived_values_are_migrated_in_place(tmp_path):
    db = tmp_path / "legacy-derived.sqlite"
    s = MemoryStore(db)
    put(s, step=1, command="echo\u00a0x")
    put(s, step=2, command="echo x")
    stale = _force_legacy_nfkc_derived_values(s)
    assert stale[0][0] == stale[1][0] == "echo x"
    assert stale[0][1] == stale[1][1]

    migrated = MemoryStore(db)
    with migrated.connect() as con:
        rows = con.execute(
            "SELECT command_norm,scientific_key FROM memories ORDER BY memory_id"
        ).fetchall()
        indexes = {row[1] for row in con.execute("PRAGMA index_list(memories)")}
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert rows[0][0] == "echo\u00a0x"
    assert rows[1][0] == "echo x"
    assert rows[0][1] != rows[1][1]
    assert "idx_memories_task_command_norm" in indexes
    assert "idx_memories_task_scientific_key" in indexes


def test_reopen_backfill_is_idempotent(tmp_path):
    db = tmp_path / "idempotent.sqlite"
    s = MemoryStore(db)
    put(s, step=1, command="echo\u00a0x")
    put(s, step=2, command="echo x")
    _force_legacy_nfkc_derived_values(s)

    first = MemoryStore(db)
    with first.connect() as con:
        values1 = tuple(
            tuple(row)
            for row in con.execute(
                "SELECT command_norm,search_norm,scientific_key FROM memories ORDER BY memory_id"
            )
        )
    second = MemoryStore(db)
    with second.connect() as con:
        values2 = tuple(
            tuple(row)
            for row in con.execute(
                "SELECT command_norm,search_norm,scientific_key FROM memories ORDER BY memory_id"
            )
        )
    assert values1 == values2


def test_deep_failed_command_recall_survives_migration_close_reopen_and_indexed_query(tmp_path):
    db = tmp_path / "deep.sqlite"
    s = MemoryStore(db)
    target = put(
        s,
        step=1,
        command=" \tpytest tests/a.py\t\n",
        content="historic deep command failure",
    )
    for i in range(350):
        s.store(
            MemoryEvent(
                task_id="t",
                step_id=100 + i,
                content=f"unrelated noise row {i}",
                kind="TOOL",
            )
        )
    _force_legacy_nfkc_derived_values(s)

    MemoryStore(db)
    reopened = MemoryStore(db)
    r = retrieve(
        "unrelated recovery planning",
        RetrievalState(task_id="t", current_step=5000, failed_command_signature="pytest tests/a.py"),
        2048,
        db_path=reopened.db_path,
    )
    assert target.memory_id in candidate_ids(r)
    assert target.memory_id in selected_ids(r)


def test_general_normalized_lexical_shadow_still_uses_nfkc_casefold():
    assert _normalize_search_text("Straße") == "strasse"
    assert _normalize_search_text("ｅｃｈｏ") == "echo"
