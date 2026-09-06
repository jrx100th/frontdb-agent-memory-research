from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import median

MANIFEST_SHA = "88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a"
TASKS = [
    "atrx-vep-crispr", "batched-eval-parity", "cad-model", "cargo-flight-dispatch",
    "coq-block-bound", "cumulative-layout-shift", "data-anonymization", "live-database-cutover",
    "music-harmony", "uefi-bootkit", "production-planning", "wdm-design",
]
ORDERS = ["ABCD", "BCDA", "CDAB", "DABC"] * 3
CONDITIONS = ["A", "B", "C", "D"]
EXPECTED = [(task, cond, pos + 1) for task, order in zip(TASKS, ORDERS) for pos, cond in enumerate(order)]


def canon(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def safe_div(a, b):
    if b in (0, None) or a is None:
        return None
    return a / b


def med(values):
    values = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return median(values) if values else None


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_records(root: Path):
    out = []
    paths = []
    for p in sorted(root.rglob("run_result.json")):
        obj = json.loads(p.read_text(encoding="utf-8"))
        out.append(obj)
        paths.append(p)
    return out, paths


def valid_accounting(r):
    return r.get("accounting_status") in {"COUNTED", "ZERO_CONFIRMED"}


def infra_invalid(r):
    f = str(r.get("failure_class") or "")
    return f.startswith("INFRASTRUCTURE_INVALID") or f.startswith("CONFIGURATION_INVALID") or f == "VERIFIER_RESULT_MISSING"


def impl_invalid(r):
    return r.get("failure_class") == "BENCHMARK_INVALID_IMPLEMENTATION_DEFECT" or bool(r.get("implementation_defect"))


def condition_metrics(records, cond):
    rows = [r for r in records if r["condition"] == cond]
    valid = [r for r in rows if valid_accounting(r)]
    successful_valid = [r for r in valid if r.get("success")]
    total_tokens = sum(int(r.get("provider_total_tokens") or 0) for r in valid)
    input_tokens = sum(int(r.get("provider_input_tokens") or 0) for r in valid)
    output_tokens = sum(int(r.get("provider_output_tokens") or 0) for r in valid)
    cached_tokens = sum(int(r.get("provider_cached_tokens") or 0) for r in valid)
    reasoning_tokens = sum(int(r.get("provider_reasoning_tokens") or 0) for r in valid)
    turns = [r.get("turns") for r in rows if isinstance(r.get("turns"), (int, float))]
    runtimes = [r.get("runtime_seconds") for r in rows if isinstance(r.get("runtime_seconds"), (int, float))]
    result = {
        "attempted": len(rows),
        "success": sum(bool(r.get("success")) for r in rows),
        "failure": sum(not bool(r.get("success")) for r in rows),
        "invalid_accounting_runs": sum(not valid_accounting(r) for r in rows),
        "infrastructure_invalid_runs": sum(infra_invalid(r) for r in rows),
        "resolution_rate": safe_div(sum(bool(r.get("success")) for r in rows), 12),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cached_tokens": cached_tokens,
        "reasoning_tokens": reasoning_tokens,
        "tokens_per_success": safe_div(total_tokens, len(successful_valid)),
        "tasks_per_1m_tokens": safe_div(len(successful_valid) * 1_000_000, total_tokens),
        "median_tokens_task": med([r.get("provider_total_tokens") for r in valid]),
        "median_tokens_success": med([r.get("provider_total_tokens") for r in successful_valid]),
        "turns": sum(turns) if turns else 0,
        "turns_per_task": safe_div(sum(turns), len(rows)) if turns else None,
        "runtime": sum(runtimes) if runtimes else 0.0,
        "median_runtime_task": med(runtimes),
        "valid_accounting_attempted": len(valid),
        "valid_accounting_success": len(successful_valid),
    }
    if cond in {"C", "D"}:
        latency_calls = []
        for r in rows:
            latency_calls.extend(x for x in (r.get("retrieval_latency_per_call_seconds") or []) if isinstance(x, (int, float)))
        result["retrieval"] = {
            "calls": len(latency_calls),
            "total_latency_seconds": sum(latency_calls),
            "median_latency_seconds": med(latency_calls),
            "db_reads": sum(int(r.get("memory_db_reads") or 0) for r in rows),
            "db_writes": sum(int(r.get("memory_db_writes") or 0) for r in rows),
            "memory_records_final_sum": sum(int(r.get("memory_record_count") or 0) for r in rows),
            "candidate_counts_sum": sum(sum(int(v or 0) for v in (r.get("retrieval_candidate_counts") or [])) for r in rows),
            "selected_counts_sum": sum(sum(int(v or 0) for v in (r.get("retrieval_selected_counts") or [])) for r in rows),
            "serialized_memory_local_units_sum": sum(sum(int(v or 0) for v in (r.get("serialized_memory_local_units") or [])) for r in rows),
            "fingerprint_file_count_sum": sum(int(r.get("fingerprint_file_count") or 0) for r in rows),
            "db_size_bytes_sum": sum(int(r.get("memory_db_size_bytes") or 0) for r in rows),
        }
    return result


def paired_metrics(records, task_set, cond):
    rows = [r for r in records if r["condition"] == cond and r["task_id"] in task_set]
    valid = [r for r in rows if valid_accounting(r)]
    total = sum(int(r.get("provider_total_tokens") or 0) for r in valid)
    success = sum(bool(r.get("success")) for r in valid)
    return {
        "task_count": len(rows),
        "success": success,
        "resolution_rate": safe_div(success, len(task_set)),
        "total_tokens": total,
        "tokens_per_success": safe_div(total, success),
    }


def reduction(base_tps, c_tps):
    if base_tps in (None, 0) or c_tps is None:
        return None
    return (base_tps - c_tps) / base_tps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    records, paths = load_records(args.input)

    pairs = [(r.get("task_id"), r.get("condition")) for r in records]
    duplicate_pairs = sorted({p for p in pairs if pairs.count(p) > 1})
    missing_pairs = [(t, c) for t, c, _ in EXPECTED if (t, c) not in set(pairs)]
    unexpected_pairs = sorted(set(pairs) - {(t, c) for t, c, _ in EXPECTED})

    schedule_errors = []
    by_pair = {(r.get("task_id"), r.get("condition")): r for r in records}
    for task_order, (task, order) in enumerate(zip(TASKS, ORDERS), 1):
        for pos, cond in enumerate(order, 1):
            r = by_pair.get((task, cond))
            if r is None:
                continue
            if r.get("task_order") != task_order or r.get("condition_order_position") != pos:
                schedule_errors.append({"task": task, "condition": cond, "expected_position": pos, "record": r.get("condition_order_position")})

    identity_errors = []
    accounting_errors = []
    isolation_errors = []
    cache_errors = []
    retry_summary = {"provider_attempts": 0, "retry_attempts": 0, "parse_failure_attempts": 0}
    runtime_images = {t: set() for t in TASKS}
    for r in records:
        if r.get("experiment_manifest_sha256") != MANIFEST_SHA:
            identity_errors.append([r.get("task_id"), r.get("condition"), "manifest"])
        if r.get("model_route") != "z-ai/glm-5.3-free":
            identity_errors.append([r.get("task_id"), r.get("condition"), "model_route"])
        if r.get("benchmark_revision") != "2b0442c3c583b710ca8da14c8e601b99f2f1f244":
            identity_errors.append([r.get("task_id"), r.get("condition"), "benchmark_revision"])
        img = r.get("task_environment_image_digest")
        if img:
            runtime_images.setdefault(r["task_id"], set()).add(img)
        attempts = r.get("provider_attempts_raw_and_normalized") or []
        retry_summary["provider_attempts"] += len(attempts)
        retry_summary["retry_attempts"] += sum(bool(a.get("retry")) for a in attempts)
        retry_summary["parse_failure_attempts"] += sum(a.get("parse_success") is False for a in attempts)
        counted_total = 0
        counted_input = 0
        counted_output = 0
        for a in attempts:
            if a.get("accounting_status") == "COUNTED":
                inp, out, total = a.get("input_tokens"), a.get("output_tokens"), a.get("total_tokens")
                if not all(type(x) is int and x >= 0 for x in (inp, out, total)) or total != inp + out:
                    accounting_errors.append([r["task_id"], r["condition"], a.get("attempt_id"), "attempt_arithmetic"])
                else:
                    counted_input += inp; counted_output += out; counted_total += total
            elif a.get("accounting_status") not in {"ZERO_CONFIRMED", "UNKNOWN", "TOKEN_ACCOUNTING_INVALID"}:
                accounting_errors.append([r["task_id"], r["condition"], a.get("attempt_id"), "unknown_status"])
        if valid_accounting(r) and r.get("accounting_status") == "COUNTED":
            if r.get("provider_input_tokens") != counted_input or r.get("provider_output_tokens") != counted_output or r.get("provider_total_tokens") != counted_total:
                accounting_errors.append([r["task_id"], r["condition"], "aggregate_arithmetic"])
        preflight_calls = r.get("provider_preflight_calls")
        if attempts and preflight_calls is not None and preflight_calls != len(attempts):
            isolation_errors.append([r["task_id"], r["condition"], "provider_preflight_count_mismatch"])
        if r.get("condition") in {"A", "B"}:
            if r.get("memory_db_reads") not in (None, 0) or r.get("memory_db_writes") not in (None, 0) or r.get("memory_record_count") not in (None, 0):
                isolation_errors.append([r["task_id"], r["condition"], "memory_side_effect"])
        if isinstance(r.get("provider_cached_tokens"), int) and isinstance(r.get("provider_input_tokens"), int):
            if r["provider_cached_tokens"] > r["provider_input_tokens"]:
                cache_errors.append([r["task_id"], r["condition"], "cached_gt_input"])

    image_drift = {t: sorted(v) for t, v in runtime_images.items() if len(v) > 1}
    if image_drift:
        isolation_errors.append(["runtime_image_drift", image_drift])

    pair_invalid_tasks = sorted({
        r["task_id"] for r in records
        if not valid_accounting(r) or infra_invalid(r)
    })
    paired_tasks = [t for t in TASKS if t not in pair_invalid_tasks]

    aggregates = {c: condition_metrics(records, c) for c in CONDITIONS}
    paired = {c: paired_metrics(records, paired_tasks, c) for c in CONDITIONS}
    comparisons = {}
    for base in ("A", "B", "D"):
        comparisons[f"C_vs_{base}"] = {
            "tokens_per_success_reduction": reduction(paired[base]["tokens_per_success"], paired["C"]["tokens_per_success"]),
            "solve_rate_delta": None if paired["C"]["resolution_rate"] is None or paired[base]["resolution_rate"] is None else paired["C"]["resolution_rate"] - paired[base]["resolution_rate"],
            "C_tokens_per_success": paired["C"]["tokens_per_success"],
            "baseline_tokens_per_success": paired[base]["tokens_per_success"],
            "C_success": paired["C"]["success"],
            "baseline_success": paired[base]["success"],
            "paired_task_count": len(paired_tasks),
        }

    has_impl = any(impl_invalid(r) for r in records)
    has_infra = bool(missing_pairs or duplicate_pairs or unexpected_pairs or schedule_errors or identity_errors or isolation_errors or any(infra_invalid(r) for r in records))
    has_accounting = bool(accounting_errors or any(not valid_accounting(r) for r in records))

    reductions = [comparisons[f"C_vs_{b}"]["tokens_per_success_reduction"] for b in ("A", "B", "D")]
    c_success = aggregates["C"]["success"]
    if has_impl:
        classification = "BENCHMARK_INVALID_IMPLEMENTATION_DEFECT"
    elif has_infra:
        classification = "INFRASTRUCTURE_INVALID_EXPERIMENT"
    elif has_accounting:
        classification = "ACCOUNTING_INVALID_EXPERIMENT"
    elif any(c_success < aggregates[b]["success"] for b in ("A", "B", "D")):
        classification = "SOLVE_RATE_REGRESSION"
    elif comparisons["C_vs_B"]["tokens_per_success_reduction"] is not None and comparisons["C_vs_B"]["tokens_per_success_reduction"] < 0.10 and aggregates["B"]["success"] >= c_success:
        classification = "LAST4_INVALIDATES_COMPLEXITY"
    elif comparisons["C_vs_D"]["tokens_per_success_reduction"] is not None and comparisons["C_vs_D"]["tokens_per_success_reduction"] < 0.10 and aggregates["D"]["success"] >= c_success:
        classification = "LEXICAL_BASELINE_INVALIDATES_COMPLEXITY"
    elif all(x is not None and x >= 0.30 for x in reductions) and all(c_success >= aggregates[b]["success"] for b in ("A", "B", "D")):
        classification = "STRONG_V0_RESULT"
    elif all(x is not None and x >= 0.20 for x in reductions) and all(c_success >= aggregates[b]["success"] for b in ("A", "B", "D")):
        classification = "WORTHWHILE_V0_RESULT"
    else:
        classification = "MODEST_OR_INCONCLUSIVE"

    invalid_ledger = [
        {
            "task_id": r["task_id"], "condition": r["condition"],
            "failure_class": r.get("failure_class"), "accounting_status": r.get("accounting_status"),
            "success": r.get("success"),
        }
        for r in records if r.get("failure_class") or not valid_accounting(r)
    ]
    index = [
        {
            "task_id": r["task_id"], "condition": r["condition"], "run_id": r.get("run_id"),
            "success": r.get("success"), "accounting_status": r.get("accounting_status"),
            "failure_class": r.get("failure_class"), "source_path": str(p), "sha256": file_sha(p),
        }
        for r, p in zip(records, paths)
    ]

    audits = {
        "record_count": len(records),
        "expected_count": 48,
        "missing_pairs": missing_pairs,
        "duplicate_pairs": duplicate_pairs,
        "unexpected_pairs": unexpected_pairs,
        "schedule_errors": schedule_errors,
        "identity_errors": identity_errors,
        "accounting_errors": accounting_errors,
        "isolation_errors": isolation_errors,
        "cache_errors": cache_errors,
        "retry_summary": retry_summary,
        "pair_invalid_tasks": pair_invalid_tasks,
        "paired_primary_tasks": paired_tasks,
        "environment_runtime_image_drift": image_drift,
    }

    summary = {
        "schema_version": 1,
        "manifest_sha256": MANIFEST_SHA,
        "planned_runs": 48,
        "completed_records": len(records),
        "missing_runs": len(missing_pairs),
        "invalid_runs": len(invalid_ledger),
        "condition_aggregates": aggregates,
        "paired_primary_aggregates": paired,
        "primary_comparisons": comparisons,
        "audits": audits,
        "outcome_classification": classification,
        "artifact_reservation": "ARTIFACT_DIGEST_LOG_METADATA_DISCREPANCY / UNRESOLVED_BUT_NONBLOCKING / RETAINED",
        "performance_reservation": "HIGH PERFORMANCE RISK / RETAINED",
    }

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "raw_run_index.json").write_bytes(canon(index))
    (args.output / "condition_aggregates.json").write_bytes(canon(aggregates))
    (args.output / "paired_primary_aggregates.json").write_bytes(canon(paired))
    (args.output / "primary_comparisons.json").write_bytes(canon(comparisons))
    (args.output / "invalid_run_ledger.json").write_bytes(canon(invalid_ledger))
    (args.output / "audit.json").write_bytes(canon(audits))
    (args.output / "summary.json").write_bytes(canon(summary))

    lines = [
        "# Frozen v0 Benchmark Execution Report", "",
        f"- Manifest: `{MANIFEST_SHA}`", f"- Records: {len(records)}/48",
        f"- Pair-valid tasks for primary comparison: {len(paired_tasks)}/12",
        f"- Outcome: **{classification}**", "",
        "## Condition aggregates", "",
        "| Condition | Success/12 | Resolution | Provider tokens | Tokens/success | Tasks/1M tokens | Runtime s |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for c in CONDITIONS:
        m = aggregates[c]
        lines.append(f"| {c} | {m['success']}/12 | {m['resolution_rate']} | {m['total_tokens']} | {m['tokens_per_success']} | {m['tasks_per_1m_tokens']} | {m['runtime']} |")
    lines += ["", "## Primary paired comparisons", "", "| Comparison | TPS reduction | Solve-rate delta | Paired tasks |", "|---|---:|---:|---:|"]
    for key in ("C_vs_A", "C_vs_B", "C_vs_D"):
        x = comparisons[key]
        lines.append(f"| {key} | {x['tokens_per_success_reduction']} | {x['solve_rate_delta']} | {x['paired_task_count']} |")
    lines += ["", "## Audit", "", f"- Missing pairs: {len(missing_pairs)}", f"- Duplicate pairs: {len(duplicate_pairs)}", f"- Accounting arithmetic errors: {len(accounting_errors)}", f"- Isolation/environment errors: {len(isolation_errors)}", f"- Invalid ledger entries: {len(invalid_ledger)}", "", "Reservations retained: ARTIFACT_DIGEST_LOG_METADATA_DISCREPANCY; HIGH PERFORMANCE RISK."]
    (args.output / "BENCHMARK_EXECUTION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    hashes = []
    for p in sorted(x for x in args.output.iterdir() if x.is_file() and x.name != "SHA256SUMS.txt"):
        hashes.append(f"{file_sha(p)}  {p.name}")
    (args.output / "SHA256SUMS.txt").write_text("\n".join(hashes) + "\n", encoding="utf-8")
    print(json.dumps({"classification": classification, "records": len(records), "missing": len(missing_pairs), "invalid": len(invalid_ledger)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
