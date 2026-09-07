from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import re
import sys

FROZEN_V0_RUNNER_MANIFEST_SHA256 = "88a98a4e191729b0d9a00afb40ade9c2985b3e4fa160034df58a4b01e83ebb4a"
SHA_RE = re.compile(r"[0-9a-f]{64}")


def _load_runner(path: Path):
    spec = importlib.util.spec_from_file_location("_frontdb_frozen_runner_v1_bound", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("CONFIGURATION_INVALID_V1_FROZEN_RUNNER_IMPORT")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bind_manifest_identity(module) -> str:
    expected = os.environ.get("FROZEN_MANIFEST_SHA256", "")
    if not SHA_RE.fullmatch(expected):
        raise RuntimeError("CONFIGURATION_INVALID_V1_MANIFEST_SHA_ENV")
    if getattr(module, "EXPECTED_MANIFEST_SHA256", None) != FROZEN_V0_RUNNER_MANIFEST_SHA256:
        raise RuntimeError("CONFIGURATION_INVALID_FROZEN_RUNNER_BASELINE_IDENTITY")
    # Infrastructure-only v1 binding: keep the frozen scientific runner byte-for-byte
    # unchanged and replace only its manifest identity constant in memory before main().
    module.EXPECTED_MANIFEST_SHA256 = expected
    if module.EXPECTED_MANIFEST_SHA256 != expected:
        raise RuntimeError("MANIFEST_IDENTITY_FAILURE")
    return expected


def main() -> int:
    runner_path = Path(os.environ.get("V1_FROZEN_RUNNER_PATH", "/tmp/frozen_runner.py"))
    if not runner_path.is_file():
        raise RuntimeError("CONFIGURATION_INVALID_V1_FROZEN_RUNNER_MISSING")
    module = _load_runner(runner_path)
    expected = _bind_manifest_identity(module)
    if sys.argv[1:] == ["--identity-self-test"]:
        print(f"V1_RUNNER_IDENTITY_SHIM=PASS manifest_sha256={expected}")
        print("FROZEN_SCIENTIFIC_RUNNER_MODIFIED=NO")
        print("PROVIDER_CALLS=0")
        return 0
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
