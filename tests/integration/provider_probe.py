from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MSWEA_SILENT_STARTUP", "1")

from minisweagent.exceptions import FormatError
from minisweagent.models.litellm_model import LitellmModel


def main() -> None:
    key = os.getenv("TOKENROUTER_API_KEY")
    base = os.getenv("TOKENROUTER_BASE_URL")
    model_name = os.getenv("TOKENROUTER_MODEL")
    Path("integration_artifacts").mkdir(exist_ok=True)
    output = Path("integration_artifacts/provider_probe.json")
    if not key or not base or not model_name:
        result = {
            "status": "BLOCKED_NO_CREDENTIALS_OR_ROUTE",
            "api_key_present": bool(key),
            "base_url_present": bool(base),
            "model_route_present": bool(model_name),
            "requested_frozen_model": "GLM-5.3",
        }
        output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(result, sort_keys=True))
        return

    model = LitellmModel(
        model_name=model_name,
        model_kwargs={"api_key": key, "api_base": base, "stream": False},
        cost_tracking="ignore_errors",
    )
    model.set_accounting_context(task_id="non-benchmark-provider-probe", run_id="integration-provider-probe")
    messages = [
        {"role": "system", "content": "This is a non-benchmark integration accounting probe."},
        {
            "role": "user",
            "content": "Call the bash tool exactly once with command: printf provider_accounting_probe",
        },
    ]
    parse_success = True
    error_type = None
    try:
        model.query(messages)
    except FormatError:
        parse_success = False
        error_type = "FormatError"
    except Exception as error:
        parse_success = False
        error_type = type(error).__name__

    attempts = model.attempt_ledger.snapshot()
    aggregate = model.attempt_ledger.aggregate()
    result = {
        "status": aggregate["accounting_status"],
        "parse_success": parse_success,
        "error_type": error_type,
        "attempt_count": len(attempts),
        "attempts": attempts,
        "aggregate": aggregate,
        "stream": False,
        "requested_frozen_model": "GLM-5.3",
        "route_model_name": model_name,
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "attempts"}, sort_keys=True))


if __name__ == "__main__":
    main()
