# Research Role Ownership

All roles may read the full repository. Ownership controls who may directly mutate role-specific or canonical material.

## Source of truth

1. current GitHub `main` HEAD
2. `state/FROZEN_VARIABLES.md` and experiment manifests
3. immutable `messages/`
4. Agent Memory Board Issue #1
5. active chat context
6. conversational memory

If memory conflicts with Git, **GIT WINS** unless the orchestrator explicitly reopens a decision.

## ORCHESTRATOR
Owns canonical scientific state:
- `state/PROJECT_STATE.md`
- `state/FROZEN_VARIABLES.md`
- `state/EXPERIMENT_VERSION`
- `decisions/DECISIONS.md`
- `agents/orchestrator/LAST_SEEN`

Other roles propose canonical-state changes through immutable messages.

## CHAT1_ARCHITECT
Owns:
- `architecture/`
- `agents/chat1_architect/LAST_SEEN`

## CHAT2_IMPLEMENTER
Owns:
- `implementation/`
- `tests/`
- message-bus helper/tests while assigned
- `agents/chat2_implementer/LAST_SEEN`

## CHAT3_REVIEWER
Owns:
- review material under `reports/review/`
- `agents/chat3_reviewer/LAST_SEEN`

## CHAT4_BENCHMARK
Owns:
- benchmark/reproducibility material
- `results/`
- `agents/chat4_benchmark/LAST_SEEN`

## Message inboxes

`messages/<role>/` is the **recipient inbox**, not sender ownership. Any role may create a new immutable message in the intended recipient's inbox. A role must never edit a historical message to change scientific meaning.

## LAST_SEEN ownership

A role may mutate **only its own** `agents/<role>/LAST_SEEN` file. The current format is documented in `HANDOFF_PROTOCOL.md`. Legacy all-zero pointers are readable migration state and should be converted only by the owning role.

## Required startup procedure

Before working, every role must read current project/frozen state, the handoff protocol, its own LAST_SEEN, and newer inbox messages. Before publishing, re-check current `main`; never force-push shared research history. Scientific-state conflicts must be escalated to the orchestrator rather than auto-resolved.
