from __future__ import annotations

import argparse
from pathlib import Path

TASKS = [
    (1, "atrx-vep-crispr", "ABCD"),
    (2, "batched-eval-parity", "BCDA"),
    (3, "cad-model", "CDAB"),
    (4, "cargo-flight-dispatch", "DABC"),
    (5, "coq-block-bound", "ABCD"),
    (6, "cumulative-layout-shift", "BCDA"),
    (7, "data-anonymization", "CDAB"),
    (8, "live-database-cutover", "DABC"),
    (9, "music-harmony", "ABCD"),
    (10, "uefi-bootkit", "BCDA"),
    (11, "production-planning", "CDAB"),
    (12, "wdm-design", "DABC"),
]


def schedule():
    out=[]
    for order,task,conds in TASKS:
        for pos,c in enumerate(conds,1):
            out.append((len(out)+1,order,task,c,pos))
    return out


def job_id(global_pos: int, task_order: int, condition: str) -> str:
    return f"r{global_pos:03d}_t{task_order:02d}_{condition.lower()}"


def build_workflow() -> str:
    seq=schedule()
    if len(seq)!=48 or len({(x[2],x[3]) for x in seq})!=48:
        raise RuntimeError("V1_EXECUTION_WORKFLOW_SCHEDULE_INVALID")
    lines=[
        "name: chat4-v1-execute-frozen-benchmark",
        "",
        "on:",
        "  workflow_dispatch:",
        "    inputs:",
        "      orchestrator_authorization:",
        "        description: 'Must equal AUTHORIZED_V1_PROVIDER_EXECUTION'",
        "        required: true",
        "        type: string",
        "",
        "permissions:",
        "  contents: read",
        "  packages: read",
        "",
        "concurrency:",
        "  group: chat4-v1-frozen-benchmark",
        "  cancel-in-progress: false",
        "",
        "env:",
        "  TOKENROUTER_BASE_URL: ${{ secrets.TOKENROUTER_BASE_URL }}",
        "  TOKENROUTER_API_KEY: ${{ secrets.TOKENROUTER_API_KEY }}",
        "  PYTHONPATH: ${{ github.workspace }}",
        "",
        "jobs:",
    ]
    prev=None
    for global_pos,order,task,condition,pos in seq:
        jid=job_id(global_pos,order,condition)
        lines.append(f"  {jid}:")
        lines.append(f"    name: {global_pos:03d}-task{order:02d}-{task}-{condition}")
        if prev:
            lines.append(f"    needs: {prev}")
        lines.extend([
            "    runs-on: ubuntu-24.04",
            "    timeout-minutes: 360",
            "    steps:",
            "      - name: Verify explicit orchestrator authorization",
            "        run: |",
            "          set -euo pipefail",
            "          test '${{ inputs.orchestrator_authorization }}' = 'AUTHORIZED_V1_PROVIDER_EXECUTION'",
            "      - name: Checkout frozen v1 execution harness",
            "        uses: actions/checkout@v4",
            "        with:",
            "          fetch-depth: 0",
            "      - name: Checkout exact Terminal-Bench",
            "        uses: actions/checkout@v4",
            "        with:",
            "          repository: harbor-framework/terminal-bench",
            "          ref: 2b0442c3c583b710ca8da14c8e601b99f2f1f244",
            "          fetch-depth: 0",
            "          path: terminal-bench",
            "      - name: Authenticate immutable image registry",
            "        env:",
            "          GHCR_TOKEN: ${{ github.token }}",
            "        run: |",
            "          set -euo pipefail",
            "          printf '%s' \"$GHCR_TOKEN\" | docker login ghcr.io -u \"$GITHUB_ACTOR\" --password-stdin",
            "      - name: Prepare exact frozen scientific harness",
            "        uses: ./.github/actions/chat4-prepare-benchmark",
            "      - name: Execute exactly one frozen v1 task-condition",
            "        run: |",
            "          set -euo pipefail",
            "          chmod +x benchmark_execution/run_v1_condition_checkpointed.sh",
            f"          ./benchmark_execution/run_v1_condition_checkpointed.sh '{task}' '{order}' '{condition}' '{pos}'",
            "      - name: Preserve raw condition evidence",
            "        if: ${{ always() }}",
            "        uses: actions/upload-artifact@v4",
            "        with:",
            f"          name: v1-raw-{global_pos:03d}-task{order:02d}-{task}-{condition}",
            "          path: |",
            f"            checkpoints-v1/{order}-{task}/{condition}",
            "            frozen-mini.tar.gz.sha256",
            "            execution-harness-sha.txt",
            "          if-no-files-found: warn",
            "          retention-days: 90",
        ])
        prev=jid
    lines.extend([
        "",
        "  execution-complete:",
        f"    needs: {prev}",
        "    runs-on: ubuntu-24.04",
        "    timeout-minutes: 10",
        "    steps:",
        "      - run: echo V1_ALL_48_CONDITIONS_CHECKPOINTED=YES",
    ])
    return "\n".join(lines)+"\n"


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    text=build_workflow()
    if text.count("Execute exactly one frozen v1 task-condition") != 48:
        raise RuntimeError("V1_EXECUTION_WORKFLOW_JOB_COUNT_INVALID")
    if "push:" in text.split("jobs:",1)[0]:
        raise RuntimeError("V1_EXECUTION_WORKFLOW_MUST_NOT_AUTO_LAUNCH")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(text,encoding="utf-8")
    print("V1_EXECUTION_JOBS=48")
    print("V1_EXECUTION_ORDER=EXACT_CHAIN")
    print("V1_EXECUTION_TRIGGER=WORKFLOW_DISPATCH_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
