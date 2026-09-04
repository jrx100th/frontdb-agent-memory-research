# Staging Test Report

## Scope

This report preserves evidence for the isolated deterministic staging implementation only. It is **not** evidence of completed authoritative mini-SWE-agent integration.

## Recorded staging evidence

```text
37 passed
compileall PASS
SQLite FTS5 PASS
SQLite integrity_check = ok
```

Required qualification:

```text
T1-T9 staging = PASS
T5a-T5h = PASS
additional adversarial tests = PASS
T10 = NOT VERIFIED
upstream mini-SWE-agent tests = NOT RUN
authoritative integration = NOT COMPLETE
Terminal-Bench = NOT RUN
```

## Recorded commands

Original isolated staging test command:

```bash
pytest -q tests/test_v0_memory.py
```

Original compile check:

```bash
python -m compileall -q src tests
```

Repository-equivalent commands after import:

```bash
PYTHONPATH=implementation/staging/src pytest -q tests/staging/test_v0_memory.py
python -m compileall -q implementation/staging/src tests/staging
```

## Evidence boundary

Do not report "all tests pass" without the word **staging**. T10 and upstream regression tests remain required before integration can pass.
