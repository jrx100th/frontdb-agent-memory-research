from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts" / "message_bus.py"
sys.path.insert(0, str(SCRIPT.parent))
import message_bus as mb

ROLES = mb.ROLES


def fixture_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for dirname in ROLES.values():
        (root / "messages" / dirname).mkdir(parents=True, exist_ok=True)
        (root / "agents" / dirname).mkdir(parents=True, exist_ok=True)
        (root / "agents" / dirname / "LAST_SEEN").write_text("0" * 40 + "\n", encoding="utf-8")
    return root


def msg(mid="MSG-000001", from_role="CHAT2_IMPLEMENTER", to="ORCHESTRATOR", *, unicode=False):
    word = "測試🙂" if unicode else "ok"
    return f"""MESSAGE_ID: {mid}
FROM: {from_role}
TO: {to}
PROJECT_VERSION: v0
SOURCE_COMMIT: {'a'*40}
CREATED_UTC: 2026-09-05T00:00:00Z
SUBJECT: {word}

SUMMARY:
{word}

VERIFIED:
- {word}

EVIDENCE:
- {word}

OPEN_QUESTIONS:
- none

REQUESTED_ACTION:
- inspect

DO_NOT_CHANGE:
- frozen variables
"""


def write_msg(root: Path, inbox: str, name: str, text: str):
    p = root / "messages" / inbox / name
    p.write_text(text, encoding="utf-8")
    return p


def test_duplicate_ids_rejected(tmp_path):
    r=fixture_repo(tmp_path)
    write_msg(r,"orchestrator","MSG-000001-a.md",msg())
    write_msg(r,"chat1_architect","MSG-000001-b.md",msg(to="CHAT1_ARCHITECT"))
    assert any("duplicate message ID" in e for e in mb.validate(r))


def test_malformed_id_rejected(tmp_path):
    r=fixture_repo(tmp_path); write_msg(r,"orchestrator","MSG-bad.md",msg(mid="MSG-12"))
    assert any("malformed MESSAGE_ID" in e for e in mb.validate(r))


def test_unknown_role_rejected(tmp_path):
    r=fixture_repo(tmp_path); write_msg(r,"orchestrator","MSG-000001-x.md",msg(from_role="UNKNOWN"))
    assert any("unknown role" in e for e in mb.validate(r))


def test_recipient_directory_must_equal_to(tmp_path):
    r=fixture_repo(tmp_path); write_msg(r,"chat3_reviewer","MSG-000001-x.md",msg(to="ORCHESTRATOR"))
    assert any("does not match TO" in e for e in mb.validate(r))


def test_required_fields_enforced(tmp_path):
    r=fixture_repo(tmp_path); write_msg(r,"orchestrator","MSG-000001-x.md",msg().replace("EVIDENCE:\n- ok\n\n", ""))
    assert any("missing fields: EVIDENCE" in e for e in mb.validate(r))


def test_last_seen_syntax_valid(tmp_path):
    r=fixture_repo(tmp_path); p=r/"agents/chat2_implementer/LAST_SEEN"
    p.write_text(f"LAST_PROCESSED_COMMIT={'b'*40}\nLAST_PROCESSED_MESSAGE=MSG-000007\nUPDATED_UTC=2026-09-05T00:00:00Z\n",encoding="utf-8")
    got=mb.parse_last_seen(p); assert got.commit=="b"*40 and got.message=="MSG-000007"


def test_role_cannot_update_another_last_seen(tmp_path, monkeypatch):
    r=fixture_repo(tmp_path); monkeypatch.setenv("FRONTDB_ROLE","CHAT2_IMPLEMENTER")
    before=(r/"agents/orchestrator/LAST_SEEN").read_bytes()
    with pytest.raises(mb.ProtocolError): mb.mark_seen(r,"ORCHESTRATOR","c"*40,"NONE")
    assert (r/"agents/orchestrator/LAST_SEEN").read_bytes()==before


def test_next_id_is_global_monotonic(tmp_path):
    r=fixture_repo(tmp_path)
    write_msg(r,"orchestrator","MSG-000002-a.md",msg(mid="MSG-000002"))
    write_msg(r,"chat3_reviewer","MSG-000009-b.md",msg(mid="MSG-000009",to="CHAT3_REVIEWER"))
    assert mb.next_id(r)=="MSG-000010"


def test_empty_inbox_works(tmp_path):
    r=fixture_repo(tmp_path); assert mb.inbox(r,"CHAT4_BENCHMARK")==[]


def test_historical_message_unchanged_by_mark_seen(tmp_path, monkeypatch):
    r=fixture_repo(tmp_path); p=write_msg(r,"chat2_implementer","MSG-000001-x.md",msg(to="CHAT2_IMPLEMENTER")); before=p.read_bytes()
    monkeypatch.setenv("FRONTDB_ROLE","CHAT2_IMPLEMENTER"); mb.mark_seen(r,"CHAT2_IMPLEMENTER","d"*40,"MSG-000001")
    assert p.read_bytes()==before


def test_corrupted_last_seen_rejected(tmp_path):
    r=fixture_repo(tmp_path); p=r/"agents/chat1_architect/LAST_SEEN"; p.write_text("garbage\n",encoding="utf-8")
    assert any("malformed LAST_SEEN" in e for e in mb.validate(r))


def test_unicode_message_parsing(tmp_path):
    r=fixture_repo(tmp_path); p=write_msg(r,"orchestrator","MSG-000001-u.md",msg(unicode=True))
    got=mb.parse_message(p,r); assert got["SUBJECT"]=="測試🙂" and mb.validate(r)==[]


def test_legacy_bootstrap_message_is_grandfathered(tmp_path):
    r=fixture_repo(tmp_path); p=r/mb.LEGACY_BOOTSTRAP; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text("""MESSAGE_ID: MSG-000001
FROM: CHAT2_IMPLEMENTER
TO: ORCHESTRATOR
PROJECT_VERSION: v0
SOURCE_COMMIT: 1111111111111111111111111111111111111111
CREATED: 2026-09-05T03:43:25+05:30
SUBJECT: legacy

SUMMARY:
legacy

VERIFIED:
legacy

OPEN QUESTIONS:
none

REQUESTED ACTION:
inspect

DO NOT CHANGE:
frozen
""",encoding="utf-8")
    assert mb.validate(r)==[]


def test_legacy_zero_last_seen_is_readable(tmp_path):
    r=fixture_repo(tmp_path); got=mb.parse_last_seen(r/"agents/chat4_benchmark/LAST_SEEN")
    assert got.commit==mb.ZERO_SHA and got.message=="NONE" and got.updated_utc=="LEGACY"
