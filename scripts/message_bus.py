#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROLES = {
    "ORCHESTRATOR": "orchestrator",
    "CHAT1_ARCHITECT": "chat1_architect",
    "CHAT2_IMPLEMENTER": "chat2_implementer",
    "CHAT3_REVIEWER": "chat3_reviewer",
    "CHAT4_BENCHMARK": "chat4_benchmark",
}
DIR_TO_ROLE = {v: k for k, v in ROLES.items()}
MSG_RE = re.compile(r"^MSG-(\d{6})$")
ZERO_SHA = "0" * 40
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CURRENT_FIELDS = {
    "MESSAGE_ID",
    "FROM",
    "TO",
    "PROJECT_VERSION",
    "SOURCE_COMMIT",
    "CREATED_UTC",
    "SUBJECT",
    "SUMMARY",
    "VERIFIED",
    "EVIDENCE",
    "OPEN_QUESTIONS",
    "REQUESTED_ACTION",
    "DO_NOT_CHANGE",
}
LEGACY_BOOTSTRAP = Path("messages/orchestrator/MSG-000001-chat2-to-orchestrator-repo-bootstrap.md")


class ProtocolError(ValueError):
    pass


@dataclass(frozen=True)
class LastSeen:
    commit: str
    message: str
    updated_utc: str


def repo_root(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    env = os.environ.get("FRONTDB_REPO_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def _role(value: str) -> str:
    role = value.upper()
    if role not in ROLES:
        raise ProtocolError(f"unknown role: {value}")
    return role


def _message_files(root: Path) -> list[Path]:
    base = root / "messages"
    return sorted(p for p in base.glob("*/*.md") if p.name.startswith("MSG-")) if base.exists() else []


def _parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key in CURRENT_FIELDS or key in {"CREATED", "OPEN QUESTIONS", "REQUESTED ACTION", "DO NOT CHANGE"}:
            fields[key] = value.strip()
    return fields


def parse_message(path: Path, root: Path) -> dict[str, str]:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ProtocolError(f"message outside repository: {path}") from exc
    text = path.read_text(encoding="utf-8")
    fields = _parse_fields(text)
    legacy = rel == LEGACY_BOOTSTRAP
    if legacy:
        required = {
            "MESSAGE_ID", "FROM", "TO", "PROJECT_VERSION", "SOURCE_COMMIT", "CREATED", "SUBJECT",
            "SUMMARY", "VERIFIED", "OPEN QUESTIONS", "REQUESTED ACTION", "DO NOT CHANGE",
        }
    else:
        required = CURRENT_FIELDS
    missing = sorted(k for k in required if k not in fields)
    if missing:
        raise ProtocolError(f"{rel}: missing fields: {', '.join(missing)}")
    msg_id = fields["MESSAGE_ID"]
    if not MSG_RE.fullmatch(msg_id):
        raise ProtocolError(f"{rel}: malformed MESSAGE_ID {msg_id!r}")
    from_role = _role(fields["FROM"])
    to_role = _role(fields["TO"])
    recipient_dir = rel.parts[1] if len(rel.parts) >= 3 else ""
    if recipient_dir != ROLES[to_role]:
        raise ProtocolError(f"{rel}: recipient directory {recipient_dir!r} does not match TO {to_role}")
    fields["FROM"] = from_role
    fields["TO"] = to_role
    fields["_PATH"] = str(rel)
    fields["_LEGACY"] = "1" if legacy else "0"
    return fields


def next_id(root: Path) -> str:
    highest = 0
    seen: set[str] = set()
    for path in _message_files(root):
        fields = parse_message(path, root)
        mid = fields["MESSAGE_ID"]
        if mid in seen:
            raise ProtocolError(f"duplicate message ID: {mid}")
        seen.add(mid)
        highest = max(highest, int(MSG_RE.fullmatch(mid).group(1)))
    return f"MSG-{highest + 1:06d}"


def parse_last_seen(path: Path, *, allow_legacy: bool = True) -> LastSeen:
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if allow_legacy and stripped == ZERO_SHA:
        return LastSeen(ZERO_SHA, "NONE", "LEGACY")
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            raise ProtocolError(f"{path}: malformed LAST_SEEN line")
        key, value = line.split("=", 1)
        if key in fields:
            raise ProtocolError(f"{path}: duplicate LAST_SEEN key {key}")
        fields[key] = value
    required = {"LAST_PROCESSED_COMMIT", "LAST_PROCESSED_MESSAGE", "UPDATED_UTC"}
    if set(fields) != required:
        raise ProtocolError(f"{path}: LAST_SEEN keys must be exactly {sorted(required)}")
    commit = fields["LAST_PROCESSED_COMMIT"]
    if commit != "NONE" and not SHA_RE.fullmatch(commit):
        raise ProtocolError(f"{path}: invalid LAST_PROCESSED_COMMIT")
    message = fields["LAST_PROCESSED_MESSAGE"]
    if message != "NONE" and not MSG_RE.fullmatch(message):
        raise ProtocolError(f"{path}: invalid LAST_PROCESSED_MESSAGE")
    try:
        stamp = fields["UPDATED_UTC"]
        if not stamp.endswith("Z"):
            raise ValueError
        datetime.fromisoformat(stamp[:-1] + "+00:00")
    except ValueError as exc:
        raise ProtocolError(f"{path}: UPDATED_UTC must be ISO8601 UTC ending Z") from exc
    return LastSeen(commit, message, fields["UPDATED_UTC"])


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    seen: dict[str, str] = {}
    for path in _message_files(root):
        try:
            fields = parse_message(path, root)
            mid = fields["MESSAGE_ID"]
            if mid in seen:
                errors.append(f"duplicate message ID {mid}: {seen[mid]} and {fields['_PATH']}")
            else:
                seen[mid] = fields["_PATH"]
        except ProtocolError as exc:
            errors.append(str(exc))
    for role, dirname in ROLES.items():
        path = root / "agents" / dirname / "LAST_SEEN"
        if not path.exists():
            errors.append(f"missing LAST_SEEN for {role}: {path.relative_to(root)}")
            continue
        try:
            parse_last_seen(path)
        except ProtocolError as exc:
            errors.append(str(exc))
    return errors


def inbox(root: Path, role: str) -> list[dict[str, str]]:
    canonical = _role(role)
    box = root / "messages" / ROLES[canonical]
    result: list[dict[str, str]] = []
    if box.exists():
        for path in sorted(box.glob("MSG-*.md")):
            result.append(parse_message(path, root))
    return result


def mark_seen(root: Path, role: str, commit: str, message: str) -> Path:
    canonical = _role(role)
    actor_raw = os.environ.get("FRONTDB_ROLE")
    if not actor_raw:
        raise ProtocolError("FRONTDB_ROLE must be set for mark-seen")
    actor = _role(actor_raw)
    if actor != canonical:
        raise ProtocolError(f"role {actor} cannot update {canonical} LAST_SEEN")
    if commit != "NONE" and not SHA_RE.fullmatch(commit):
        raise ProtocolError("invalid commit SHA")
    if message != "NONE" and not MSG_RE.fullmatch(message):
        raise ProtocolError("invalid message ID")
    path = root / "agents" / ROLES[canonical] / "LAST_SEEN"
    if not path.parent.is_dir():
        raise ProtocolError(f"missing role directory: {path.parent}")
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    path.write_text(
        f"LAST_PROCESSED_COMMIT={commit}\n"
        f"LAST_PROCESSED_MESSAGE={message}\n"
        f"UPDATED_UTC={stamp}\n",
        encoding="utf-8",
    )
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic Git+Markdown agent message-bus helper")
    parser.add_argument("--root", help="repository root (default: script parent repo or FRONTDB_REPO_ROOT)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    sub.add_parser("next-id")
    p_inbox = sub.add_parser("inbox"); p_inbox.add_argument("role")
    sub.add_parser("status")
    p_seen = sub.add_parser("mark-seen"); p_seen.add_argument("role"); p_seen.add_argument("commit"); p_seen.add_argument("message")
    args = parser.parse_args(argv)
    root = repo_root(args.root)
    try:
        if args.cmd == "validate":
            errors = validate(root)
            if errors:
                for e in errors: print(f"ERROR: {e}", file=sys.stderr)
                return 1
            print("VALID")
        elif args.cmd == "next-id":
            print(next_id(root))
        elif args.cmd == "inbox":
            for item in inbox(root, args.role): print(f"{item['MESSAGE_ID']}\t{item['_PATH']}")
        elif args.cmd == "status":
            errors = validate(root)
            print(f"validation={'PASS' if not errors else 'FAIL'}")
            print(f"next_id={next_id(root) if not errors else 'UNKNOWN'}")
            for role, dirname in ROLES.items():
                ls = parse_last_seen(root / "agents" / dirname / "LAST_SEEN")
                print(f"{role} commit={ls.commit} message={ls.message} updated={ls.updated_utc}")
            if errors: return 1
        elif args.cmd == "mark-seen":
            print(mark_seen(root, args.role, args.commit, args.message))
    except ProtocolError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
