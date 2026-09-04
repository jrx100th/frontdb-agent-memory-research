from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import math
import re
import sqlite3
from typing import Iterable

from .context_builder import serialized_message_units
from .fingerprint import compare_fingerprint, fingerprint
from .store import MemoryRecord, _row_to_record

RETRIEVAL_BUDGET = 2048
MAX_SELECTED = 8
MAX_PER_STEP = 2
CANDIDATE_POOL_MAX = 40
Q_LOCAL_MAX = 20
Q_TASK_MAX = 10
CURRENT_STATE_TYPES = {"STATE_CHANGE", "TOOL_RESULT", "OBSERVED"}
HISTORICAL_TYPES = {"ERROR", "FAILED_APPROACH", "TEST_RESULT"}
EVIDENCE = {"VERIFIED": 1.0, "OBSERVED": 0.6, "UNVERIFIED": 0.0}
STOP = {"the","and","for","with","that","this","from","into","your","you","are","was","were","has","have","had","not","but","can","will","all","our","out","use","using","then","than","when","where","what"}
WORD_RE = re.compile(r"\w+", re.UNICODE)

@dataclass
class RetrievalState:
    task_id: str
    current_step: int
    workspace: str | None = None
    task_text: str = ""
    file_paths: list[str] = field(default_factory=list)
    error_signature: str | None = None
    failed_command_signature: str | None = None

@dataclass
class RetrievalResult:
    candidates: list[dict]
    filtered: list[dict]
    selected: list[dict]
    serialized_records: list[dict]
    serialized_memory_units: int


def _terms(text: str) -> set[str]:
    return {w.casefold() for w in WORD_RE.findall(text) if len(w) >= 3 and w.casefold() not in STOP}


def _fts_query(text: str) -> str:
    toks = [t for t in WORD_RE.findall(text) if len(t) >= 2]
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in toks[:32])


def _paths(record: MemoryRecord) -> set[str]:
    return set(record.file_paths)


def _freshness(record: MemoryRecord, state: RetrievalState) -> str:
    if not record.file_fingerprints:
        return "UNKNOWN" if record.file_paths else "NOT_APPLICABLE"
    if not state.workspace:
        return "UNKNOWN"
    statuses: list[str] = []
    for old in record.file_fingerprints:
        current = fingerprint(old.get("path", ""), state.workspace)
        statuses.append(compare_fingerprint(old, current))
    if "STALE" in statuses:
        return "STALE"
    if "UNKNOWN" in statuses:
        return "UNKNOWN"
    return "FRESH"


def _record_json(record: MemoryRecord, freshness: str) -> dict:
    return {
        "command": record.command,
        "content": record.content,
        "file_paths": list(record.file_paths),
        "freshness": freshness,
        "importance": record.importance,
        "memory_id": record.memory_id,
        "memory_type": record.memory_type,
        "outcome": record.outcome,
        "source_ref": record.source_ref,
        "step_id": record.step_id,
        "verification_status": record.verification_status,
    }


def _jaccard(a: str, b: str) -> float:
    aa, bb = _terms(a), _terms(b)
    if not aa and not bb:
        return 1.0
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(aa | bb)


def retrieve(query: str, state: RetrievalState, budget_tokens: int, *, db_path: str | Path) -> RetrievalResult:
    budget = min(RETRIEVAL_BUDGET, max(0, int(budget_tokens)))
    if budget <= 0:
        return RetrievalResult([], [], [], [], 0)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    cutoff = state.current_step - 4
    base_sql = "task_id=? AND step_id < ? AND invalidated_by IS NULL"
    candidate_rank: dict[int, int] = {}
    candidate_source: dict[int, set[str]] = {}

    def add_fts(text: str, limit: int, source: str) -> None:
        q = _fts_query(text)
        if not q:
            return
        rows = con.execute(
            f"""SELECT m.*, bm25(memories_fts) AS b FROM memories_fts
                JOIN memories m ON m.memory_id=memories_fts.rowid
                WHERE memories_fts MATCH ? AND m.{base_sql}
                ORDER BY b ASC, m.step_id DESC, m.memory_id ASC LIMIT ?""",
            (q, state.task_id, cutoff, limit),
        ).fetchall()
        for rank, row in enumerate(rows, 1):
            mid = int(row["memory_id"])
            candidate_rank[mid] = min(candidate_rank.get(mid, 10**9), rank)
            candidate_source.setdefault(mid, set()).add(source)

    add_fts(query, Q_LOCAL_MAX, "local")
    add_fts(state.task_text, Q_TASK_MAX, "task")

    # Supplemental candidate scan is bounded before scoring and only over eligible task-local history.
    supplemental = con.execute(
        f"SELECT * FROM memories WHERE {base_sql} ORDER BY step_id DESC, memory_id ASC LIMIT 200",
        (state.task_id, cutoff),
    ).fetchall()
    qterms, taskterms = _terms(query), _terms(state.task_text)
    current_paths = set(state.file_paths)
    for row in supplemental:
        if len(candidate_rank) >= CANDIDATE_POOL_MAX:
            break
        try:
            rec = _row_to_record(row)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        text = " ".join(filter(None, [rec.content, rec.command or "", rec.source_ref or ""]))
        terms = _terms(text)
        salient = len(taskterms & terms)
        file_hit = bool(current_paths & _paths(rec))
        err_hit = bool(state.error_signature and state.error_signature.casefold() in text.casefold())
        cmd_hit = bool(state.failed_command_signature and rec.command and state.failed_command_signature.strip() == rec.command.strip())
        if salient >= 2 or file_hit or err_hit or cmd_hit:
            candidate_rank.setdefault(rec.memory_id, 10**6)
            candidate_source.setdefault(rec.memory_id, set()).add("supplemental")

    mids = sorted(candidate_rank)[:CANDIDATE_POOL_MAX]
    if not mids:
        con.close()
        return RetrievalResult([], [], [], [], 0)
    marks = ",".join("?" for _ in mids)
    rows = con.execute(f"SELECT * FROM memories WHERE memory_id IN ({marks})", mids).fetchall()
    con.close()
    recs = {}
    for row in rows:
        try:
            recs[row["memory_id"]] = _row_to_record(row)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue

    candidates: list[dict] = []
    scored: list[tuple[float, MemoryRecord, str, dict]] = []
    for mid, rank in candidate_rank.items():
        rec = recs.get(mid)
        if rec is None:
            continue
        text = " ".join(filter(None, [rec.content, rec.command or "", rec.source_ref or ""]))
        terms = _terms(text)
        local_match = "local" in candidate_source.get(mid, set()) and bool(qterms & terms)
        salient_overlap = len(taskterms & terms)
        file_overlap = 1.0 if current_paths & _paths(rec) else 0.0
        err_match = bool(state.error_signature and state.error_signature.casefold() in text.casefold())
        cmd_match = bool(state.failed_command_signature and rec.command and state.failed_command_signature.strip() == rec.command.strip())
        failure_test_match = 1.0 if (err_match or cmd_match) else 0.0
        eligible_signal = local_match or salient_overlap >= 2 or bool(file_overlap) or err_match or cmd_match
        freshness = _freshness(rec, state)
        excluded = (rec.memory_type in CURRENT_STATE_TYPES and freshness in {"STALE", "UNKNOWN"})
        lexical_rr = 0.0 if rank >= 10**6 else 1.0 / rank
        score = lexical_rr * 1.00 + file_overlap * 0.35 + failure_test_match * 0.30 + EVIDENCE.get(rec.verification_status, 0.0) * 0.15 + rec.importance * 0.10
        meta = {
            "memory_id": rec.memory_id, "rank": rank, "sources": sorted(candidate_source.get(mid, set())),
            "local_match": local_match, "task_salient_overlap": salient_overlap, "file_overlap": file_overlap,
            "failure_test_match": failure_test_match, "freshness": freshness, "score": round(score, 6),
            "eligible_signal": bool(eligible_signal), "excluded_current_stale_unknown": excluded,
        }
        candidates.append(meta)
        if eligible_signal and not excluded:
            scored.append((score, rec, freshness, meta))

    scored.sort(key=lambda x: (-x[0], -x[1].step_id, x[1].memory_id))
    # Exact and near-duplicate collapse after scoring so the strongest equivalent survives.
    deduped: list[tuple[float, MemoryRecord, str, dict]] = []
    seen_fp: set[str] = set()
    for item in scored:
        rec = item[1]
        if rec.fingerprint in seen_fp:
            continue
        if any(_jaccard(rec.content, kept[1].content) >= 0.85 for kept in deduped):
            continue
        seen_fp.add(rec.fingerprint)
        deduped.append(item)

    selected: list[dict] = []
    selected_records: list[dict] = []
    per_step: dict[int, int] = {}
    for score, rec, freshness, meta in deduped:
        if len(selected_records) >= MAX_SELECTED:
            break
        if per_step.get(rec.step_id, 0) >= MAX_PER_STEP:
            continue
        serial = _record_json(rec, freshness)
        trial = selected_records + [serial]
        if serialized_message_units(trial) > budget:
            continue
        selected_records.append(serial)
        selected.append({**meta, "content": rec.content})
        per_step[rec.step_id] = per_step.get(rec.step_id, 0) + 1

    size = serialized_message_units(selected_records) if selected_records else 0
    filtered = [{**meta, "selected": any(s["memory_id"] == meta["memory_id"] for s in selected)} for _, _, _, meta in deduped]
    return RetrievalResult(candidates, filtered, selected, selected_records, size)
