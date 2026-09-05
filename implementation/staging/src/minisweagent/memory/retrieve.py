from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import re
import sqlite3

from .context_builder import serialized_message_units
from .fingerprint import compare_fingerprint, fingerprint
from .store import MemoryRecord, _row_to_record

RETRIEVAL_BUDGET = 2048
MAX_SELECTED = 8
MAX_PER_STEP = 2
CANDIDATE_POOL_MAX = 40
Q_LOCAL_MAX = 20
Q_TASK_MAX = 10
# Internal scan bound only: the frozen Q_* constants still cap the number of
# diverse FTS candidates admitted from each query.
FTS_SCAN_MAX = 4096
SIGNATURE_SCAN_MAX = 512
CURRENT_STATE_TYPES = {"STATE_CHANGE", "TOOL_RESULT", "OBSERVED"}
HISTORICAL_TYPES = {"ERROR", "FAILED_APPROACH", "TEST_RESULT"}
EVIDENCE = {"VERIFIED": 1.0, "OBSERVED": 0.6, "UNVERIFIED": 0.0}
STOP = {"the","and","for","with","that","this","from","into","your","you","are","was","were","has","have","had","not","but","can","will","all","our","out","use","using","then","than","when","where","what"}
WORD_RE = re.compile(r"\w+", re.UNICODE)
NUMBER_RE = re.compile(r"[+-]?\d+(?:\.\d+)?")

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


def _lower_terms(text: str) -> set[str]:
    return {w.lower() for w in WORD_RE.findall(text) if len(w) >= 3 and w.lower() not in STOP}


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


def _norm_optional(value: str | None) -> str:
    return (value or "").strip().casefold()


def _material_values(text: str) -> tuple[str, ...]:
    return tuple(NUMBER_RE.findall(text))


def _dedup_equivalent(a: MemoryRecord, b: MemoryRecord) -> bool:
    """Return True only when collapsing the records cannot erase material state."""
    if a.memory_type != b.memory_type:
        return False
    if a.verification_status != b.verification_status:
        return False
    if _norm_optional(a.outcome) != _norm_optional(b.outcome):
        return False
    if _norm_optional(a.command) != _norm_optional(b.command):
        return False
    if _material_values(a.content) != _material_values(b.content):
        return False
    if a.fingerprint == b.fingerprint:
        return True
    return _jaccard(a.content, b.content) >= 0.85


def _materially_conflicts(a: MemoryRecord, b: MemoryRecord) -> bool:
    outcome_conflict = (
        bool(_norm_optional(a.outcome))
        and bool(_norm_optional(b.outcome))
        and _norm_optional(a.outcome) != _norm_optional(b.outcome)
        and _norm_optional(a.command) == _norm_optional(b.command)
    )
    exact_state_conflict = a.fingerprint == b.fingerprint and (
        a.verification_status != b.verification_status
        or a.memory_type != b.memory_type
        or _norm_optional(a.outcome) != _norm_optional(b.outcome)
    )
    numeric_conflict = (
        _jaccard(a.content, b.content) >= 0.85
        and _material_values(a.content) != _material_values(b.content)
        and bool(_material_values(a.content) or _material_values(b.content))
    )
    return outcome_conflict or exact_state_conflict or numeric_conflict


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
            (q, state.task_id, cutoff, FTS_SCAN_MAX),
        ).fetchall()
        diverse: list[MemoryRecord] = []
        for row in rows:
            try:
                rec = _row_to_record(row)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            if any(_dedup_equivalent(rec, prior) for prior in diverse):
                continue
            diverse.append(rec)
            rank = len(diverse)
            mid = rec.memory_id
            candidate_rank[mid] = min(candidate_rank.get(mid, 10**9), rank)
            candidate_source.setdefault(mid, set()).add(source)
            if rank >= limit:
                break

    def add_error_signature(text: str) -> None:
        q = _fts_query(text)
        if not q:
            return
        rows = con.execute(
            f"""SELECT m.*, bm25(memories_fts) AS b FROM memories_fts
                JOIN memories m ON m.memory_id=memories_fts.rowid
                WHERE memories_fts MATCH ? AND m.{base_sql}
                ORDER BY b ASC, m.step_id DESC, m.memory_id ASC LIMIT ?""",
            (q, state.task_id, cutoff, SIGNATURE_SCAN_MAX),
        ).fetchall()
        needle = text.casefold()
        admitted = 0
        for row in rows:
            joined = " ".join(filter(None, [row["content"], row["command"] or "", row["source_ref"] or ""]))
            if needle not in joined.casefold():
                continue
            admitted += 1
            mid = int(row["memory_id"])
            candidate_rank[mid] = min(candidate_rank.get(mid, 10**9), 10**6 + admitted)
            candidate_source.setdefault(mid, set()).add("error_signature")
            if admitted >= CANDIDATE_POOL_MAX:
                break

    def add_failed_command(command: str) -> None:
        rows = con.execute(
            f"""SELECT * FROM memories WHERE {base_sql} AND command=?
                ORDER BY step_id DESC, memory_id ASC LIMIT ?""",
            (state.task_id, cutoff, command.strip(), CANDIDATE_POOL_MAX),
        ).fetchall()
        for rank, row in enumerate(rows, 1):
            mid = int(row["memory_id"])
            candidate_rank[mid] = min(candidate_rank.get(mid, 10**9), 10**6 + rank)
            candidate_source.setdefault(mid, set()).add("failed_command")

    add_fts(query, Q_LOCAL_MAX, "local")
    add_fts(state.task_text, Q_TASK_MAX, "task")
    if state.error_signature:
        add_error_signature(state.error_signature)
    if state.failed_command_signature:
        add_failed_command(state.failed_command_signature)

    # Bounded task-local supplement for file/task signals and normalization-only
    # lexical matches that FTS5 unicode61 does not surface (for example ß vs ss).
    supplemental = con.execute(
        f"SELECT * FROM memories WHERE {base_sql} ORDER BY step_id DESC, memory_id ASC LIMIT 200",
        (state.task_id, cutoff),
    ).fetchall()
    qterms, taskterms = _terms(query), _terms(state.task_text)
    q_lower_terms = _lower_terms(query)
    current_paths = set(state.file_paths)
    for supplement_rank, row in enumerate(supplemental, 1):
        if len(candidate_rank) >= CANDIDATE_POOL_MAX and not state.error_signature and not state.failed_command_signature:
            break
        try:
            rec = _row_to_record(row)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        text = " ".join(filter(None, [rec.content, rec.command or "", rec.source_ref or ""]))
        terms = _terms(text)
        lower_terms = _lower_terms(text)
        salient = len(taskterms & terms)
        file_hit = bool(current_paths & _paths(rec))
        err_hit = bool(state.error_signature and state.error_signature.casefold() in text.casefold())
        cmd_hit = bool(state.failed_command_signature and rec.command and state.failed_command_signature.strip() == rec.command.strip())
        normalization_hit = bool(qterms & terms) and not bool(q_lower_terms & lower_terms)
        if salient >= 2 or file_hit or err_hit or cmd_hit or normalization_hit:
            candidate_rank.setdefault(rec.memory_id, 10**6 + supplement_rank)
            source = "normalized_local" if normalization_hit else "supplemental"
            candidate_source.setdefault(rec.memory_id, set()).add(source)

    explicit = sorted(
        (mid for mid, sources in candidate_source.items() if {"error_signature", "failed_command"} & sources),
        key=lambda mid: (candidate_rank[mid], mid),
    )
    explicit_set = set(explicit)
    ordinary = sorted(
        (mid for mid in candidate_rank if mid not in explicit_set),
        key=lambda mid: (candidate_rank[mid], mid),
    )
    mids = (explicit + ordinary)[:CANDIDATE_POOL_MAX]
    if not mids:
        con.close()
        return RetrievalResult([], [], [], [], 0)
    marks = ",".join("?" for _ in mids)
    rows = con.execute(f"SELECT * FROM memories WHERE memory_id IN ({marks})", mids).fetchall()
    con.close()
    recs: dict[int, MemoryRecord] = {}
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
        sources = candidate_source.get(mid, set())
        local_match = bool(qterms & terms) and bool({"local", "normalized_local"} & sources)
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
            "memory_id": rec.memory_id, "rank": rank, "sources": sorted(sources),
            "local_match": local_match, "task_salient_overlap": salient_overlap, "file_overlap": file_overlap,
            "failure_test_match": failure_test_match, "freshness": freshness, "score": round(score, 6),
            "eligible_signal": bool(eligible_signal), "excluded_current_stale_unknown": excluded,
            "suppressed_by_verified_conflict": False,
        }
        candidates.append(meta)
        if eligible_signal and not excluded:
            scored.append((score, rec, freshness, meta))

    scored.sort(key=lambda x: (-x[0], -x[1].step_id, x[1].memory_id))

    # A newer VERIFIED contradiction can suppress an older UNVERIFIED hypothesis
    # for selection without changing frozen ranking coefficients.
    verified = [item for item in scored if item[1].verification_status == "VERIFIED"]
    conflict_filtered: list[tuple[float, MemoryRecord, str, dict]] = []
    for item in scored:
        rec = item[1]
        suppressed = rec.verification_status == "UNVERIFIED" and any(
            newer[1].step_id > rec.step_id and _materially_conflicts(rec, newer[1])
            for newer in verified
        )
        if suppressed:
            item[3]["suppressed_by_verified_conflict"] = True
            continue
        conflict_filtered.append(item)

    # Exact and near-duplicate collapse after scoring. Equivalence includes
    # verification/outcome/command/material values so contradictions survive.
    deduped: list[tuple[float, MemoryRecord, str, dict]] = []
    for item in conflict_filtered:
        rec = item[1]
        if any(_dedup_equivalent(rec, kept[1]) for kept in deduped):
            continue
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
