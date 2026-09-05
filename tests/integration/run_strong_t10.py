from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def run_fixture(source: Path, output: Path, *, patched: bool) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(source / "src")
    env["PATCHED"] = "1" if patched else "0"
    env["MSWEA_SILENT_STARTUP"] = "1"
    with tempfile.TemporaryDirectory() as td:
        env["MSWEA_GLOBAL_CONFIG_DIR"] = td
        subprocess.run(
            [sys.executable, str(Path(__file__).with_name("t10_fixture.py")), str(output)],
            check=True,
            env=env,
        )
    return json.loads(output.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pristine", type=Path, required=True)
    parser.add_argument("--patched", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    pristine = run_fixture(args.pristine, args.out / "t10_pristine.json", patched=False)
    patched = run_fixture(args.patched, args.out / "t10_patched.json", patched=True)

    checks = {
        "provider_messages_identical": pristine["canonical_request"] == patched["canonical_request"],
        "provider_config_identical": pristine["canonical_provider_config"] == patched["canonical_provider_config"],
        "tool_structure_identical": pristine["canonical_tool_schema"] == patched["canonical_tool_schema"],
        "db_writes_disabled": patched["memory_side_effects"]["db_writes"] == 0,
        "db_connections_disabled": patched["memory_side_effects"]["sqlite_connect_calls"] == 0,
        "fingerprints_disabled": patched["memory_side_effects"]["fingerprints"] == 0,
        "retrieval_disabled": patched["memory_side_effects"]["retrieval"] == 0,
        "context_disabled": patched["memory_side_effects"]["context"] == 0,
        "runtime_init_disabled": patched["memory_side_effects"]["runtime_init"] == 0,
        "synthetic_message_disabled": patched["memory_side_effects"]["synthetic_messages_in_request"] == 0,
    }
    checks["PASS"] = all(checks.values())
    (args.out / "strong_t10.json").write_text(json.dumps(checks, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(checks, sort_keys=True))
    if not checks["PASS"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
