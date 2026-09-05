from __future__ import annotations

from pathlib import Path
import sys

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts" / "message_bus.py"
sys.path.insert(0, str(SCRIPT.parent))
import message_bus as mb


def fixture_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for dirname in mb.ROLES.values():
        (root / "messages" / dirname).mkdir(parents=True, exist_ok=True)
        (root / "agents" / dirname).mkdir(parents=True, exist_ok=True)
        (root / "agents" / dirname / "LAST_SEEN").write_text("0" * 40 + "\n", encoding="utf-8")
    return root


def message(mid: str, to: str = "ORCHESTRATOR") -> str:
    return f"""MESSAGE_ID: {mid}
FROM: CHAT2_IMPLEMENTER
TO: {to}
PROJECT_VERSION: v0
SOURCE_COMMIT: {'a'*40}
CREATED_UTC: 2026-09-05T00:00:00Z
SUBJECT: CAS test

SUMMARY:
cas

VERIFIED:
- cas

EVIDENCE:
- cas

OPEN_QUESTIONS:
- none

REQUESTED_ACTION:
- none

DO_NOT_CHANGE:
- frozen
"""


def test_two_allocators_from_same_head_stale_second_must_reallocate(tmp_path):
    root = fixture_repo(tmp_path)
    head0 = "1" * 40
    # Two agents see the same repository state and initially propose the same ID.
    assert mb.next_id(root, expected_head=head0, current_head=head0) == "MSG-000001"
    assert mb.next_id(root, expected_head=head0, current_head=head0) == "MSG-000001"

    # Agent A publishes first and main advances.
    p = root / "messages/orchestrator/MSG-000001-a.md"
    p.write_text(message("MSG-000001"), encoding="utf-8")
    head1 = "2" * 40

    # Agent B's stale expected-head publication is rejected; after reread it reallocates.
    with pytest.raises(mb.ProtocolError, match="HEAD changed"):
        mb.next_id(root, expected_head=head0, current_head=head1)
    assert mb.next_id(root, expected_head=head1, current_head=head1) == "MSG-000002"


def test_cas_requires_both_head_values_and_valid_shas(tmp_path):
    root = fixture_repo(tmp_path)
    with pytest.raises(mb.ProtocolError, match="supplied together"):
        mb.next_id(root, expected_head="1" * 40)
    with pytest.raises(mb.ProtocolError, match="invalid HEAD SHA"):
        mb.next_id(root, expected_head="not-a-sha", current_head="not-a-sha")
