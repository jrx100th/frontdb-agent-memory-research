from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import hashlib
import json
import sqlite3
import unicodedata

from .fingerprint import fingerprint

MAX_CHUNK_UNITS = 256
COMMAND_BOUNDARY_NOISE = " \t\n"


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: int
    task_id: str
    step_id: int
    memory_type: str
    content: str
    source_ref: str | None
    file_paths: tuple[str, ...]
    command: str | None
    outcome: str | None
    verification_status: str
    importance: int
    token_count: int
    fingerprint: str
    file_fingerprints: tuple[dict, ...]
    supersedes: int | None
    invalidated_by: int | None


@dataclass
class MemoryEvent:
    task_id: str
    step_id: int
    content: str
    kind: str
    source_ref: str | None = None
    file_paths: list[str] = field(default_factory=list)
    command: str | None = None
    outcome: str | None = None
    returncode: int | None = None
    memory_type: str | None = None
    verification_status: str | None = None
    importance: int | None = None
    supersedes: int | None = None
    workspace: str | None = None


def local_units(text: str) -> int:
    return len(text.encode("utf-8"))


def _split_utf8(text: str, max_units: int = MAX_CHUNK_UNITS) -> list[str]:
    if max_units <= 0:
        return []
    out: list[str] = []
    cur: list[str] = []
    used = 0
    for ch in text:
        n = len(ch.encode("utf-8"))
        if cur and used + n > max_units:
            out.append("".join(cur))
            cur, used = [], 0
        if n > max_units:
            continue
        cur.append(ch)
        used += n
    if cur or not out:
        out.append("".join(cur))
    return out


def _policy(event: MemoryEvent) -> tuple[str, str, int]:
    if event.memory_type and event.verification_status and event.importance is not None:
        return event.memory_type, event.verification_status, event.importance
    kind = event.kind.upper()
    if kind == "ASSISTANT":
        return "HYPOTHESIS", "UNVERIFIED", 1
    if event.returncode not in (None, 0):
        return "ERROR", "OBSERVED", event.importance or 2
    if event.memory_type:
        mtype = event.memory_type
    elif "test" in (event.command or "").lower() or "pytest" in event.content.lower():
        mtype = "TEST_RESULT"
    elif event.outcome and event.outcome.upper() in {"FAILED", "FAILURE"}:
        mtype = "FAILED_APPROACH"
    else:
        mtype = "TOOL_RESULT"
    return mtype, event.verification_status or "OBSERVED", event.importance or 1


def _command_lookup_key(value: str | None) -> str:
    """Conservative failed-command lookup key.

    Only ASCII shell boundary transport noise proven equivalent by the staging
    Bash tests is removed. Internal code points, Unicode compatibility forms,
    quoting, punctuation, and Unicode whitespace are preserved byte-for-byte.
    """
    if value is None:
        return ""
    return value.strip(COMMAND_BOUNDARY_NOISE)


def _normalize_command(value: str | None) -> str:
    # Backward-compatible internal name for the persisted command_norm lookup key.
    return _command_lookup_key(value)


def _raw_command_sha256(value: str | None) -> str:
    if value is None:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_search_text(*parts: str | None) -> str:
    joined = " ".join(p for p in parts if p)
    return " ".join(unicodedata.normalize("NFKC", joined).casefold().split())


def _canonical_file_paths(paths: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(dict.fromkeys(str(p) for p in paths)))


def _canonical_file_fingerprints(fps: list[dict] | tuple[dict, ...]) -> tuple[str, ...]:
    return tuple(
        sorted(json.dumps(fp, sort_keys=True, separators=(",", ":"), ensure_ascii=True) for fp in fps)
    )


def _scientific_key(
    *,
    content_fingerprint: str,
    memory_type: str,
    verification_status: str,
    outcome: str | None,
    command: str | None,
    file_paths: list[str] | tuple[str, ...],
    file_fingerprints: list[dict] | tuple[dict, ...],
) -> str:
    payload = {
        "content_fingerprint": content_fingerprint,
        "memory_type": memory_type,
        "verification_status": verification_status,
        "outcome": (outcome or "").strip().casefold(),
        "command_lookup_key": _command_lookup_key(command),
        "raw_command_sha256": _raw_command_sha256(command),
        "file_paths": _canonical_file_paths(file_paths),
        "file_fingerprints": _canonical_file_fingerprints(file_fingerprints),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _row_to_record(row: sqlite3.Row) -> MemoryRecord:
    return MemoryRecord(
        memory_id=row["memory_id"],
        task_id=row["task_id"],
        step_id=row["step_id"],
        memory_type=row["memory_type"],
        content=row["content"],
        source_ref=row["source_ref"],
        file_paths=tuple(json.loads(row["file_paths"])),
        command=row["command"],
        outcome=row["outcome"],
        verification_status=row["verification_status"],
        importance=row["importance"],
        token_count=row["token_count"],
        fingerprint=row["fingerprint"],
        file_fingerprints=tuple(json.loads(row["file_fingerprints"])),
        supersedes=row["supersedes"],
        invalidated_by=row["invalidated_by"],
    )


class MemoryStore:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        schema = Path(__file__).with_name("schema.sql").read_text()
        with self.connect() as con:
            exists = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='memories'"
            ).fetchone()
            if exists:
                columns = {row["name"] for row in con.execute("PRAGMA table_info(memories)")}
                additions = {
                    "command_norm": "TEXT NOT NULL DEFAULT ''",
                    "search_norm": "TEXT NOT NULL DEFAULT ''",
                    "scientific_key": "TEXT NOT NULL DEFAULT ''",
                }
                for name, ddl in additions.items():
                    if name not in columns:
                        con.execute(f"ALTER TABLE memories ADD COLUMN {name} {ddl}")
            con.executescript(schema)
            self._backfill_derived(con)

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _backfill_derived(self, con: sqlite3.Connection) -> None:
        # Recompute all persisted derived identities so databases written under
        # the previous NFKC command rule migrate deterministically in place.
        rows = con.execute("SELECT * FROM memories").fetchall()
        rebuild_norm_fts = False
        for row in rows:
            paths = list(json.loads(row["file_paths"]))
            fps = list(json.loads(row["file_fingerprints"]))
            command_norm = _command_lookup_key(row["command"])
            search_norm = _normalize_search_text(row["content"], row["command"], row["source_ref"])
            key = _scientific_key(
                content_fingerprint=row["fingerprint"],
                memory_type=row["memory_type"],
                verification_status=row["verification_status"],
                outcome=row["outcome"],
                command=row["command"],
                file_paths=paths,
                file_fingerprints=fps,
            )
            if search_norm != row["search_norm"]:
                rebuild_norm_fts = True
            if (
                command_norm != row["command_norm"]
                or search_norm != row["search_norm"]
                or key != row["scientific_key"]
            ):
                con.execute(
                    "UPDATE memories SET command_norm=?, search_norm=?, scientific_key=? WHERE memory_id=?",
                    (command_norm, search_norm, key, row["memory_id"]),
                )
        memory_count = con.execute("SELECT count(*) FROM memories").fetchone()[0]
        norm_count = con.execute("SELECT count(*) FROM memories_norm_fts").fetchone()[0]
        if rebuild_norm_fts or memory_count != norm_count:
            con.execute("DELETE FROM memories_norm_fts")
            con.execute(
                "INSERT INTO memories_norm_fts(rowid,search_norm,task_id,memory_id) "
                "SELECT memory_id,search_norm,task_id,memory_id FROM memories"
            )

    def store(self, event: MemoryEvent | dict[str, Any]) -> list[MemoryRecord]:
        if isinstance(event, dict):
            event = MemoryEvent(**event)
        mtype, verification, importance = _policy(event)
        paths = list(dict.fromkeys(str(p) for p in event.file_paths))
        file_fps: list[dict] = []
        if event.workspace:
            file_fps = [fingerprint(p, event.workspace).to_dict() for p in paths]
        chunks = _split_utf8(event.content)
        created: list[MemoryRecord] = []
        with self.connect() as con:
            for idx, chunk in enumerate(chunks):
                content_fp = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
                source_ref = event.source_ref if len(chunks) == 1 else f"{event.source_ref or 'event'}#chunk={idx}"
                command_norm = _command_lookup_key(event.command)
                search_norm = _normalize_search_text(chunk, event.command, source_ref)
                scientific_key = _scientific_key(
                    content_fingerprint=content_fp,
                    memory_type=mtype,
                    verification_status=verification,
                    outcome=event.outcome,
                    command=event.command,
                    file_paths=paths,
                    file_fingerprints=file_fps,
                )
                cur = con.execute(
                    """INSERT INTO memories(task_id,step_id,memory_type,content,source_ref,file_paths,command,outcome,
                       verification_status,importance,token_count,fingerprint,file_fingerprints,command_norm,search_norm,
                       scientific_key,supersedes,invalidated_by)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)""",
                    (
                        event.task_id,
                        event.step_id,
                        mtype,
                        chunk,
                        source_ref,
                        json.dumps(paths, separators=(",", ":"), ensure_ascii=True),
                        event.command,
                        event.outcome,
                        verification,
                        importance,
                        local_units(chunk),
                        content_fp,
                        json.dumps(file_fps, sort_keys=True, separators=(",", ":"), ensure_ascii=True),
                        command_norm,
                        search_norm,
                        scientific_key,
                        event.supersedes,
                    ),
                )
                new_id = int(cur.lastrowid)
                if event.supersedes is not None:
                    con.execute(
                        "UPDATE memories SET invalidated_by=? WHERE memory_id=? AND task_id=? AND invalidated_by IS NULL",
                        (new_id, event.supersedes, event.task_id),
                    )
                row = con.execute("SELECT * FROM memories WHERE memory_id=?", (new_id,)).fetchone()
                created.append(_row_to_record(row))
        return created

    def get(self, memory_id: int) -> MemoryRecord | None:
        with self.connect() as con:
            row = con.execute("SELECT * FROM memories WHERE memory_id=?", (memory_id,)).fetchone()
        return _row_to_record(row) if row else None


def store(event: MemoryEvent | dict[str, Any], *, db_path: str | Path) -> list[MemoryRecord]:
    return MemoryStore(db_path).store(event)