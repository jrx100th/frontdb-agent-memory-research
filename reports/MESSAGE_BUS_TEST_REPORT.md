# Agent Memory Bus Validation Report

Scope: coordination infrastructure only. No experiment runtime, retrieval, model, harness, T10, or Terminal-Bench execution is involved.

Validation evidence:

```text
python -m compileall -q scripts tests/message_bus
PASS

pytest -q tests/message_bus/test_message_bus.py
14 passed

python scripts/message_bus.py --root <legacy-local-snapshot> validate
VALID

python scripts/message_bus.py --root <legacy-local-snapshot> next-id
MSG-000002
```

Covered deterministic cases:

1. duplicate message IDs rejected
2. malformed message IDs rejected
3. unknown roles rejected
4. recipient directory must equal `TO`
5. required current-schema fields enforced
6. current LAST_SEEN syntax validated
7. role cannot update another role's LAST_SEEN through helper
8. next ID is globally monotonic
9. empty inbox works
10. historical message bytes unchanged by `mark-seen`
11. corrupted LAST_SEEN rejected
12. Unicode message parsing
13. immutable legacy bootstrap message is grandfathered
14. legacy zero LAST_SEEN sentinel is readable

Result: **PASS** for the tested message-bus helper/protocol behavior.
