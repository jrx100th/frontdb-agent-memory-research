from pathlib import Path

BUS = Path("scripts/message_bus.py")
text = BUS.read_text(encoding="utf-8")

old_sig = "def next_id(root: Path) -> str:\n    highest = 0\n"
new_sig = '''def _validate_head(value: str) -> str:\n    if not SHA_RE.fullmatch(value):\n        raise ProtocolError(f"invalid HEAD SHA: {value!r}")\n    return value\n\n\ndef assert_expected_head(expected_head: str, current_head: str) -> None:\n    expected = _validate_head(expected_head)\n    current = _validate_head(current_head)\n    if expected != current:\n        raise ProtocolError(\n            f"HEAD changed from {expected} to {current}; reread messages, reallocate ID, and retry"\n        )\n\n\ndef next_id(\n    root: Path,\n    *,\n    expected_head: str | None = None,\n    current_head: str | None = None,\n) -> str:\n    if (expected_head is None) != (current_head is None):\n        raise ProtocolError("expected_head and current_head must be supplied together")\n    if expected_head is not None:\n        assert_expected_head(expected_head, current_head)\n    highest = 0\n'''
if old_sig in text:
    text = text.replace(old_sig, new_sig, 1)
elif "def assert_expected_head(" not in text:
    raise SystemExit("next_id signature marker missing")

old_parser = '    sub.add_parser("next-id")\n'
new_parser = '''    p_next = sub.add_parser("next-id")\n    p_next.add_argument("--expected-head")\n    p_next.add_argument("--current-head")\n'''
if old_parser in text:
    text = text.replace(old_parser, new_parser, 1)
elif 'p_next.add_argument("--expected-head")' not in text:
    raise SystemExit("next-id parser marker missing")

old_dispatch = '''        elif args.cmd == "next-id":\n            print(next_id(root))\n'''
new_dispatch = '''        elif args.cmd == "next-id":\n            print(next_id(root, expected_head=args.expected_head, current_head=args.current_head))\n'''
if old_dispatch in text:
    text = text.replace(old_dispatch, new_dispatch, 1)
elif "expected_head=args.expected_head" not in text:
    raise SystemExit("next-id dispatch marker missing")

BUS.write_text(text, encoding="utf-8")

PROTOCOL = Path("HANDOFF_PROTOCOL.md")
protocol = PROTOCOL.read_text(encoding="utf-8")
section = '''## Concurrent global-ID publication\n\n`next-id` without HEAD arguments is advisory only. A concurrent publisher must use optimistic HEAD/CAS publication:\n\n1. read the current `main` HEAD as `expected_head`;\n2. reread inbox/message IDs and allocate the next global ID against that HEAD;\n3. optionally run `message_bus.py next-id --expected-head <sha> --current-head <sha>` as a local stale-HEAD guard;\n4. create the publication commit with `expected_head` as its parent;\n5. update `main` using a non-force fast-forward ref update;\n6. if HEAD changed or the ref update fails, discard/rebuild the unpushed communication commit, reread messages, reallocate the global ID, and retry.\n\nThe non-force expected-parent ref update is the publication CAS. This preserves multi-chat autonomy without Redis, a broker, or a lock service. Previously published research commits are never rewritten.\n\n'''
marker = "## Agent Memory Board — Issue #1\n"
if "## Concurrent global-ID publication" not in protocol:
    if marker not in protocol:
        raise SystemExit("protocol insertion marker missing")
    protocol = protocol.replace(marker, section + marker, 1)
PROTOCOL.write_text(protocol, encoding="utf-8")

print("message-bus CAS source/protocol updated")
