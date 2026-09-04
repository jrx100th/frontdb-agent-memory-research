# Research Role Ownership

All roles may read the full repository. Ownership below controls who may directly change canonical material after bootstrap.

## ORCHESTRATOR
Owns:
- `state/PROJECT_STATE.md`
- `state/FROZEN_VARIABLES.md`
- `state/EXPERIMENT_VERSION`
- `decisions/DECISIONS.md`

Other roles propose changes through immutable messages.

## CHAT1_ARCHITECT
Owns:
- `architecture/`
- `messages/chat1_architect/`
- `agents/chat1_architect/LAST_SEEN`

## CHAT2_IMPLEMENTER
Owns:
- `implementation/`
- `tests/`
- `messages/chat2_implementer/`
- `agents/chat2_implementer/LAST_SEEN`

## CHAT3_REVIEWER
Owns:
- review material under `reports/review/`
- `messages/chat3_reviewer/`
- `agents/chat3_reviewer/LAST_SEEN`

## CHAT4_BENCHMARK
Owns:
- benchmark configuration/results/reproducibility material
- `messages/chat4_benchmark/`
- `agents/chat4_benchmark/LAST_SEEN`

## Required startup procedure

Before working, every role must:
1. read `state/PROJECT_STATE.md`;
2. read `state/FROZEN_VARIABLES.md`;
3. read its inbox for immutable messages newer than its own `LAST_SEEN` commit;
4. perform only work consistent with the frozen variables;
5. after processing inbox messages, update only its own `LAST_SEEN`.
