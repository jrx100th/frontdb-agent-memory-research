# Immutable Handoff Protocol

The repository, not conversational memory, is canonical.

## Inbox layout

Each receiver has an inbox:

- `messages/orchestrator/`
- `messages/chat1_architect/`
- `messages/chat2_implementer/`
- `messages/chat3_reviewer/`
- `messages/chat4_benchmark/`

A message is an immutable Markdown file. Example:

`messages/chat3_reviewer/MSG-000001-chat2-to-chat3-implementation-review.md`

## Required message format

```text
MESSAGE_ID:
FROM:
TO:
PROJECT_VERSION:
SOURCE_COMMIT:
CREATED:
SUBJECT:

SUMMARY:

VERIFIED:

OPEN QUESTIONS:

REQUESTED ACTION:

DO NOT CHANGE:
```

## Rules

1. Never edit another role's historical message.
2. Corrections create a new message with a new message ID.
3. One significant handoff should be one commit.
4. Commit SHAs are part of the audit trail.
5. Never depend on chat memory when canonical repository state exists.
6. Before working, read `PROJECT_STATE.md` and `FROZEN_VARIABLES.md`.
7. Read inbox messages newer than your own `LAST_SEEN` commit.
8. After processing those messages, update only your own `LAST_SEEN` file.
9. Message numbers are monotonic within each receiver inbox.
10. Do not rewrite or squash research-history commits unless the orchestrator explicitly orders it.

## LAST_SEEN semantics

`agents/<role>/LAST_SEEN` contains the commit SHA through which that role has processed its inbox. The bootstrap value of forty zeroes means no inbox commit has yet been acknowledged.

## Commit subjects

- `[ORCH] ...`
- `[ARCH] ...`
- `[IMPL] ...`
- `[REVIEW] ...`
- `[BENCH] ...`
