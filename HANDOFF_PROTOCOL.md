# Durable Agent Memory / Handoff Protocol

GitHub `main` is the durable shared memory. Markdown message files are immutable scientific handoffs. GitHub Issue #1 is the live coordination board.

## Source-of-truth priority

1. current GitHub `main` HEAD
2. `state/FROZEN_VARIABLES.md` and experiment manifests
3. immutable `messages/`
4. Agent Memory Board Issue #1
5. active chat context
6. conversational memory

If conversational memory conflicts with Git, **GIT WINS** unless the orchestrator explicitly reopens a decision.

## Roles and recipient inboxes

- `ORCHESTRATOR` -> `messages/orchestrator/`
- `CHAT1_ARCHITECT` -> `messages/chat1_architect/`
- `CHAT2_IMPLEMENTER` -> `messages/chat2_implementer/`
- `CHAT3_REVIEWER` -> `messages/chat3_reviewer/`
- `CHAT4_BENCHMARK` -> `messages/chat4_benchmark/`

The directory names the **recipient**. Example: `messages/chat3_reviewer/` contains messages TO Chat 3.

## Current durable message schema

Every new message uses:

```text
MESSAGE_ID:
FROM:
TO:
PROJECT_VERSION:
SOURCE_COMMIT:
CREATED_UTC:
SUBJECT:

SUMMARY:

VERIFIED:

EVIDENCE:

OPEN_QUESTIONS:

REQUESTED_ACTION:

DO_NOT_CHANGE:
```

Messages are UTF-8 Markdown and immutable after commit. If a message is wrong, create a new globally numbered correction message and reference the earlier message ID. Never edit historical scientific meaning.

### Legacy bootstrap compatibility

`messages/orchestrator/MSG-000001-chat2-to-orchestrator-repo-bootstrap.md` predates this schema and remains immutable. The helper recognizes that exact file as grandfathered legacy format. All new messages must use the current schema.

## Global message IDs

IDs are globally monotonic across every recipient inbox:

```text
MSG-000001
MSG-000002
MSG-000003
...
```

Before allocating, scan all `messages/*/MSG-*.md`; use highest existing ID + 1. Duplicate or malformed IDs are invalid.

## LAST_SEEN pointers

Each role owns only its own `agents/<role>/LAST_SEEN`.

Current format:

```text
LAST_PROCESSED_COMMIT=<40-hex-sha-or-NONE>
LAST_PROCESSED_MESSAGE=<MSG-ID-or-NONE>
UPDATED_UTC=<ISO8601-UTC-ending-Z>
```

The historical forty-zero single-line value is accepted as a read-only legacy sentinel. Only the owning role may migrate its pointer to current format.

## Startup / publish procedure

1. sync/read latest `main`;
2. read `state/PROJECT_STATE.md`;
3. read `state/FROZEN_VARIABLES.md`;
4. read this protocol;
5. read own LAST_SEEN;
6. discover/process newer own-inbox messages in ID order;
7. perform assigned work;
8. create immutable outgoing messages;
9. update only own LAST_SEEN;
10. re-check current remote state before publishing;
11. never force-push or rewrite published research history.

If concurrent work causes a conflict in `state/`, `architecture/`, or `manifests/`, stop and escalate to the orchestrator. Do not auto-resolve scientific-state conflicts.

## Concurrent global-ID publication

`next-id` without HEAD arguments is advisory only. A concurrent publisher must use optimistic HEAD/CAS publication:

1. read the current `main` HEAD as `expected_head`;
2. reread inbox/message IDs and allocate the next global ID against that HEAD;
3. optionally run `message_bus.py next-id --expected-head <sha> --current-head <sha>` as a local stale-HEAD guard;
4. create the publication commit with `expected_head` as its parent;
5. update `main` using a non-force fast-forward ref update;
6. if HEAD changed or the ref update fails, discard/rebuild the unpushed communication commit, reread messages, reallocate the global ID, and retry.

The non-force expected-parent ref update is the publication CAS. This preserves multi-chat autonomy without Redis, a broker, or a lock service. Previously published research commits are never rewritten.

## Agent Memory Board — Issue #1

Issue #1 is the live short-handoff layer. Durable scientific state remains in Git. Board comments are append-only in meaning; corrections are new `BMSG-XXXXXX` comments rather than edits.

## Deterministic helper

`scripts/message_bus.py` is stdlib-only and supports:

```text
validate
next-id
inbox ROLE
status
mark-seen ROLE COMMIT MESSAGE_ID
```

`mark-seen` requires `FRONTDB_ROLE` to equal the role whose pointer is being updated, preventing normal helper use from mutating another role's LAST_SEEN.
