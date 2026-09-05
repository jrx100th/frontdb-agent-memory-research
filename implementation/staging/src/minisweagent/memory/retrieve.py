from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import re
import sqlite3

from .context_builder import serialized_message_units
from .fingerprint import compare_fingerprint, fingerprint
from .store import MemoryRecord, _normalize_command, _normalize_search_text, _raw_command_sha256, _row_to_record

RETRIEVAL_BUDGET = 2048
MAX_SELECTED = 8
MAX_PER_STEP = 2
CANDIDATE_POOL_MAX = 40
Q_LOCAL_MAX = 20
Q_TASK_MAX = 10
SUPPLEMENTAL_CANDIDATE_LIMIT = 10
FTS_PAGE_SIZE = 256
CURRENT_STATE_TYPES = {"STATE_CHANGE", "TOOL_RESULT", "OBSERVED"}
HISTORICAL_TYPES = {"ERROR", "FAILED_APPROACH", "TEST_RESULT"}
EVIDENCE = {"VERIFIED": 1.0, "OBSERVED": 0.6, "UNVERIFIED": 0.0}
STOP = {"the","and","for","with","that","this","from","into","your","you","are","was","were","has","have","had","not","but","can","will","all","our","out","use","using","then","than","when","where","what"}
WORD_RE = re.compile(r"\w+", re.UNICODE)
NUMBER_RE = re.compile(r"[+-]?\d+(?:\.\d+)?")
SIGNATURE_RE = re.compile(r"\w+", re.UNICODE)


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
    normalized = _normalize_search_text(text)
    return {w for w in WORD_RE.findall(normalized) if len(w) >= 3 and w not in STOP}


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


def _canonical_file_state(record: MemoryRecord) -> tuple[tuple[str, ...], tuple[str, ...]]:
    paths = tuple(sorted(record.file_paths))
    fps = tuple(
        sorted(json.dumps(fp, sort_keys=True, separators=(",", ":"), ensure_ascii=True) for fp in record.file_fingerprints)
    )
    return paths, fps


def _dedup_equivalent(a: MemoryRecord, b: MemoryRecord) -> bool:
    if a.memory_type != b.memory_type:
        return False
    if a.verification_status != b.verification_status:
        return False
    if _norm_optional(a.outcome) != _norm_optional(b.outcome):
        return False
    if _raw_command_sha256(a.command) != _raw_command_sha256(b.command):
        return False
    if _normalize_command(a.command) != _normalize_command(b.command):
        return False
    if _material_values(a.content) != _material_values(b.content):
        return False
    if _canonical_file_state(a) != _canonical_file_state(b):
        return False
    if a.fingerprint == b.fingerprint:
        return True
    return _jaccard(a.content, b.content) >= 0.85


def _materially_conflicts(a: MemoryRecord, b: MemoryRecord) -> bool:
    outcome_conflict = (
        bool(_norm_optional(a.outcome))
        and bool(_norm_optional(b.outcome))
        and _norm_optional(a.outcome) != _norm_optional(b.outcome)
        and _normalize_command(a.command) == _normalize_command(b.command)
    )
    exact_state_conflict = a.fingerprint == b.fingerprint and (
        a.verification_status != b.verification_status
        or a.memory_type != b.memory_type
        or _norm_optional(a.outcome) != _norm_optional(b.outcome)
        or _canonical_file_state(a) != _canonical_file_state(b)
    )
    numeric_conflict = (
        _jaccard(a.content, b.content) >= 0.85
        and _material_values(a.content) != _material_values(b.content)
        and bool(_material_values(a.content) or _material_values(b.content))
    )
    return outcome_conflict or exact_state_conflict or numeric_conflict


def _signature_tokens(text: str) -> tuple[str, ...]:
    return tuple(SIGNATURE_RE.findall(_normalize_search_text(text)))


def _signature_match(signature: str | None, text: str) -> bool:
    if not signature:
        return False
    needle = _signature_tokens(signature)
    haystack = _signature_tokens(text)
    if not needle or len(needle) > len(haystack):
        return False
    n = len(needle)
    return any(haystack[i:i+n] == needle for i in range(len(haystack) - n + 1))


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
    candidate_records: dict[int, MemoryRecord] = {}
    qterms, taskterms = _terms(query), _terms(state.task_text)
    current_paths = set(state.file_paths)

    eq_expr = "COALESCE(NULLIF(scientific_key,''), fingerprint || char(31) || memory_type || char(31) || verification_status || char(31) || coalesce(outcome,'') || char(31) || trim(coalesce(command,'')) || char(31) || file_paths || char(31) || file_fingerprints)"

    def iter_fts(text: str, *, normalized: bool = False):
        search = _normalize_search_text(text) if normalized else text
        q = _fts_query(search)
        if not q:
            return
        table = "memories_norm_fts" if normalized else "memories_fts"
        offset = 0
        diverse: list[MemoryRecord] = []
        while True:
            rows = con.execute(
                f"""WITH matched AS (
                        SELECT m.*, {table}.rank AS b
                        FROM {table} JOIN memories m ON m.memory_id={table}.rowid
                        WHERE {table} MATCH ? AND m.{base_sql}
                    ), ranked AS (
                        SELECT matched.*, ROW_NUMBER() OVER (
                            PARTITION BY {eq_expr}
                            ORDER BY b ASC, step_id DESC, memory_id ASC
                        ) AS eq_rank
                        FROM matched
                    )
                    SELECT * FROM ranked WHERE eq_rank=1
                    ORDER BY b ASC, step_id DESC, memory_id ASC LIMIT ? OFFSET ?""",
                (q, state.task_id, cutoff, FTS_PAGE_SIZE, offset),
            ).fetchall()
            if not rows:
                break
            for row in rows:
                try:
                    rec = _row_to_record(row)
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
                if any(_dedup_equivalent(rec, prior) for prior in diverse):
                    continue
                diverse.append(rec)
                yield rec
            if len(rows) < FTS_PAGE_SIZE:
                break
            offset += len(rows)

    def add_primary(text: str, limit: int, source: str) -> None:
        rank = 0
        for rec in iter_fts(text):
            rank += 1
            mid = rec.memory_id
            candidate_records[mid] = rec
            candidate_rank[mid] = min(candidate_rank.get(mid, 10**9), rank)
            candidate_source.setdefault(mid, set()).add(source)
            if rank >= limit:
                break

    supplemental_offers: list[tuple[int, int, MemoryRecord, str]] = []

    def offer(priority: int, rank: int, rec: MemoryRecord, source: str) -> None:
        supplemental_offers.append((priority, rank, rec, source))

    add_primary(query, Q_LOCAL_MAX, "local")
    add_primary(state.task_text, Q_TASK_MAX, "task")

    if state.error_signature:
        exact_rank = 0
        for rec in iter_fts(state.error_signature):
            text = " ".join(filter(None, [rec.content, rec.command or "", rec.source_ref or ""]))
            if not _signature_match(state.error_signature, text):
                continue
            exact_rank += 1
            offer(0, exact_rank, rec, "error_signature")
            if exact_rank >= SUPPLEMENTAL_CANDIDATE_LIMIT:
                break

    if state.failed_command_signature:
        normalized_command = _normalize_command(state.failed_command_signature)
        rows = con.execute(
            f"""WITH ranked AS (
                    SELECT *, ROW_NUMBER() OVER (
                        PARTITION BY {eq_expr}
                        ORDER BY step_id DESC, memory_id ASC
                    ) AS eq_rank
                    FROM memories WHERE {base_sql} AND command_norm=?
                )
                SELECT * FROM ranked WHERE eq_rank=1
                ORDER BY step_id DESC, memory_id ASC LIMIT ?""",
            (state.task_id, cutoff, normalized_command, SUPPLEMENTAL_CANDIDATE_LIMIT),
        ).fetchall()
        for rank, row in enumerate(rows, 1):
            try:
                rec = _row_to_record(row)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            offer(0, rank, rec, "failed_command")

    # Indexed NFKC+casefold shadow retrieval. This is supplemental only; the
    # frozen primary lexical retriever remains FTS5 unicode61 over memories_fts.
    norm_rank = 0
    for rec in iter_fts(query, normalized=True):
        if rec.memory_id in candidate_records or any(_dedup_equivalent(rec, prior) for prior in candidate_records.values()):
            continue
        norm_rank += 1
        offer(1, norm_rank, rec, "normalized_local")
        if norm_rank >= SUPPLEMENTAL_CANDIDATE_LIMIT:
            break

    # Bounded recent supplement for file/task signals only. Normalization and
    # explicit signatures no longer depend on this recency window.
    supplemental = con.execute(
        f"SELECT * FROM memories WHERE {base_sql} ORDER BY step_id DESC, memory_id ASC LIMIT 200",
        (state.task_id, cutoff),
    ).fetchall()
    for supplement_rank, row in enumerate(supplemental, 1):
        try:
            rec = _row_to_record(row)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        text = " ".join(filter(None, [rec.content, rec.command or "", rec.source_ref or ""]))
        terms = _terms(text)
        salient = len(taskterms & terms)
        file_hit = bool(current_paths & _paths(rec))
        err_hit = _signature_match(state.error_signature, text)
        cmd_hit = bool(
            state.failed_command_signature
            and rec.command
            and _normalize_command(state.failed_command_signature) == _normalize_command(rec.command)
        )
        if salient >= 2 or file_hit or err_hit or cmd_hit:
            offer(2, supplement_rank, rec, "supplemental")

    supplemental_offers.sort(key=lambda x: (x[0], x[1], -x[2].step_id, x[2].memory_id))
    supplemental_admitted = 0
    for _, _, rec, source in supplemental_offers:
        if rec.memory_id in candidate_records:
            candidate_source.setdefault(rec.memory_id, set()).add(source)
            continue
        equivalent_mid = next(
            (mid for mid, existing in candidate_records.items() if _dedup_equivalent(rec, existing)),
            None,
        )
        if equivalent_mid is not None:
            candidate_source.setdefault(equivalent_mid, set()).add(source)
            continue
        if supplemental_admitted >= SUPPLEMENTAL_CANDIDATE_LIMIT:
            break
        supplemental_admitted += 1
        candidate_records[rec.memory_id] = rec
        candidate_rank[rec.memory_id] = 10**6 + supplemental_admitted
        candidate_source.setdefault(rec.memory_id, set()).add(source)

    mids = sorted(candidate_rank, key=lambda mid: (candidate_rank[mid], mid))[:CANDIDATE_POOL_MAX]
    if not mids:
        con.close()
        return RetrievalResult([], [], [], [], 0)
    con.close()

    candidates: list[dict] = []
    scored: list[tuple[float, MemoryRecord, str, dict]] = []
    for mid in mids:
        rank = candidate_rank[mid]
        rec = candidate_records[mid]
        text = " ".join(filter(None, [rec.content, rec.command or "", rec.source_ref or ""]))
        terms = _terms(text)
        sources = candidate_source.get(mid, set())
        # Admission from either indexed lexical source is itself deterministic
        # evidence of a lexical match; do not discard short (e.g. Greek) tokens
        # through the >=3 salient-term filter used for task overlap.
        local_match = bool({"local", "normalized_local"} & sources)
        salient_overlap = len(taskterms & terms)
        file_overlap = 1.0 if current_paths & _paths(rec) else 0.0
        err_match = _signature_match(state.error_signature, text)
        cmd_match = bool(
            state.failed_command_signature
            and rec.command
            and _normalize_command(state.failed_command_signature) == _normalize_command(rec.command)
        )
        failure_test_match = 1.0 if (err_match or cmd_match) else 0.0
        eligible_signal = local_match or salient_overlap >= 2 or bool(file_overlap) or err_match or cmd_match
        freshness = _freshness(rec, state)
        excluded = rec.memory_type in CURRENT_STATE_TYPES and freshness in {"STALE", "UNKNOWN"}
        lexical_rr = 0.0 if rank >= 10**6 else 1.0 / rank
        score = lexical_rr * 1.00 + file_overlap * 0.35 + failure_test_match * 0.30 + EVIDENCE.get(rec.verification_status, 0.0) * 0.15 + rec.importance * 0.10
        meta = {
            "memory_id": rec.memory_id,
            "rank": rank,
            "sources": sorted(sources),
            "local_match": local_match,
            "task_salient_overlap": salient_overlap,
            "file_overlap": file_overlap,
            "failure_test_match": failure_test_match,
            "freshness": freshness,
            "score": round(score, 6),
            "eligible_signal": bool(eligible_signal),
            "excluded_current_stale_unknown": excluded,
            "suppressed_by_verified_conflict": False,
        }
        candidates.append(meta)
        if eligible_signal and not excluded:
            scored.append((score, rec, freshness, meta))

    scored.sort(key=lambda x: (-x[0], -x[1].step_id, x[1].memory_id))
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
    filtered = [
        {**meta, "selected": any(s["memory_id"] == meta["memory_id"] for s in selected)}
        for _, _, _, meta in deduped
    ]
    return RetrievalResult(candidates, filtered, selected, selected_records, size)