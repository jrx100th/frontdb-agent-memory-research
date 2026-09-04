# Agent Memory Efficiency Experiment

Controlled open-source research repository for agent-memory token-efficiency experiments using mini-SWE-agent and Terminal-Bench.

This repository is the durable shared memory and asynchronous coordination bus for:

- `ORCHESTRATOR`
- `CHAT1_ARCHITECT`
- `CHAT2_IMPLEMENTER`
- `CHAT3_REVIEWER`
- `CHAT4_BENCHMARK`

## Source of truth

Priority is strict:

1. current GitHub `main` HEAD
2. `state/FROZEN_VARIABLES.md` and experiment manifests
3. immutable files under `messages/`
4. Agent Memory Board — GitHub Issue #1
5. active chat context
6. conversational memory

If conversational memory conflicts with Git, **GIT WINS** unless the orchestrator explicitly reopens a decision.

## Startup procedure

Before doing research work, every role must:

1. sync/read current `main`;
2. read `state/PROJECT_STATE.md`;
3. read `state/FROZEN_VARIABLES.md`;
4. read `HANDOFF_PROTOCOL.md`;
5. read only its own `agents/<role>/LAST_SEEN` pointer;
6. process newer files in its recipient inbox under `messages/<role>/` in global message-ID order;
7. perform only work consistent with frozen state;
8. write immutable outgoing message files as needed;
9. update only its own `LAST_SEEN`;
10. publish without rewriting previously published scientific history.

## Current experiment boundary

The v0 architecture is frozen. The deterministic memory implementation is staged and tested in isolation, but authoritative mini-SWE-agent integration is incomplete. T10 remains **NOT VERIFIED**. Terminal-Bench remains **NOT RUN**. The final experiment manifest remains **NOT FROZEN**.

## Security

Never commit API keys, TokenRouter credentials, cookies, access tokens, private keys, `.env` files, or other secrets.

## Provenance

The initial working-tree snapshot was imported through the authenticated GitHub API because native Git transport was unavailable in the implementation runtime. Original local commit SHAs and the pre-import file SHA-256 manifest are recorded under `provenance/`.
