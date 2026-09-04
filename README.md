# Agent Memory Efficiency Experiment

Controlled research repository for agent-memory token-efficiency experiments using mini-SWE-agent and Terminal-Bench.

This repository is the canonical source of truth and asynchronous communication bus for five research roles:

- `ORCHESTRATOR`
- `CHAT1_ARCHITECT`
- `CHAT2_IMPLEMENTER`
- `CHAT3_REVIEWER`
- `CHAT4_BENCHMARK`

## Current status

The v0 architecture is frozen. A deterministic memory implementation is staged and tested in isolation, but it is **not yet integrated into an authoritative mini-SWE-agent v2.4.6 checkout**. Terminal-Bench has **not** been run.

Before doing research work, read:

1. `state/PROJECT_STATE.md`
2. `state/FROZEN_VARIABLES.md`
3. `HANDOFF_PROTOCOL.md`
4. messages in your inbox newer than the commit recorded in your own `agents/<role>/LAST_SEEN`

Git history is the scientific audit trail. Do not squash or rewrite research history unless explicitly ordered by the orchestrator.

## Security

Never commit API keys, TokenRouter credentials, cookies, access tokens, `.env` files, or other secrets.
