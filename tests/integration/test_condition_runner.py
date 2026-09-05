from __future__ import annotations

import copy
from dataclasses import asdict
from pathlib import Path
import sqlite3

import pytest

from minisweagent.agents.default import DefaultAgent


class StaticModelConfig:
    def model_dump(self, *args, **kwargs):
        return {
            "model_name": "z-ai/glm-5.3-free",
            "custom_llm_provider": "openai",
            "stream": False,
            "litellm_version": "1.99.0",
        }


class CaptureModel:
    tool_schema = {"type": "function", "function": {"name": "bash", "parameters": {"type": "object"}}}

    def __init__(self):
        self.calls = 0
        self.last_messages = None
        self.config = StaticModelConfig()

    def query(self, messages, **kwargs):
        self.calls += 1
        self.last_messages = copy.deepcopy(messages)
        return {"role": "assistant", "content": "captured", "extra": {"actions": [], "cost": 0.0}}

    def format_message(self, **kwargs):
        return dict(kwargs)

    def format_observation_messages(self, message, outputs, template_vars=None):
        return []

    def get_template_vars(self, **kwargs):
        return {}

    def serialize(self):
        return {"info": {"config": {"model": self.config.model_dump()}}}


class FakeEnv:
    def get_template_vars(self):
        return {}

    def execute(self, action, cwd=""):
        return {"output": "ok", "returncode": 0}

    def serialize(self):
        return {"info": {"config": {"environment": "fake"}}}


def native_step(step: int, *, text: str | None = None):
    text = text or f"step-{step}"
    tool_id = f"tc-{step}"
    return [
        {
            "role": "assistant",
            "content": f"assistant-{step}",
            "extra": {"actions": [{"command": f"printf {step}", "tool_call_id": tool_id}]},
            "_verbatim_marker": f"assistant-private-{step}",
        },
        {
            "role": "tool",
            "tool_call_id": tool_id,
            "content": f"<returncode>0</returncode>\n<output>{text}</output>",
            "extra": {"returncode": 0, "raw_output": text},
            "_verbatim_marker": f"tool-private-{step}",
        },
    ]


def make_agent(
    tmp_path: Path,
    condition: str,
    *,
    task: str = "task alpha beta",
    task_id: str = "task-1",
    memory_enabled: bool = False,
    db_name: str = "condition.sqlite",
):
    model = CaptureModel()
    env = FakeEnv()
    agent = DefaultAgent(
        model=model,
        env=env,
        system_template="SYSTEM {{ task }}",
        instance_template="TASK {{ task }}",
        step_limit=0,
        cost_limit=0.0,
        wall_time_limit_seconds=0,
        max_consecutive_format_errors=3,
        memory_enabled=memory_enabled,
        memory_db_path=tmp_path / db_name,
        memory_task_id=task_id,
        memory_workspace=tmp_path,
        benchmark_condition=condition,
    )
    agent.extra_template_vars = {"task": task}
    if agent._memory_runtime is not None:
        agent._memory_runtime.start_task(task, task_id=task_id)
    agent.messages = [
        model.format_message(role="system", content=agent._render_template(agent.config.system_template)),
        model.format_message(role="user", content=agent._render_template(agent.config.instance_template)),
    ]
    return agent, model, env


def has_memory_message(messages) -> bool:
    return any(
        m.get("role") == "user" and str(m.get("content", "")).startswith("HISTORICAL_MEMORY_DATA_V1")
        for m in messages
    )


def install_memory_bombs(monkeypatch):
    import minisweagent.memory.integration as integration
    import minisweagent.memory.retrieve as retrieve_mod
    import minisweagent.memory.store as store_mod

    class BombRuntime:
        def __init__(self, *args, **kwargs):
            raise AssertionError("MemoryRuntime must not be instantiated")

    def bomb(*args, **kwargs):
        raise AssertionError("memory/retrieval/fingerprint side effect must not execute")

    monkeypatch.setattr(integration, "MemoryRuntime", BombRuntime)
    monkeypatch.setattr(integration, "retrieve", bomb)
    monkeypatch.setattr(retrieve_mod, "fingerprint", bomb)
    monkeypatch.setattr(store_mod, "fingerprint", bomb)
    monkeypatch.setattr(sqlite3, "connect", bomb)


def test_selector_rejects_invalid_condition_fail_closed(tmp_path):
    with pytest.raises(ValueError, match="Unknown benchmark_condition"):
        make_agent(tmp_path, "b")
    with pytest.raises(ValueError, match="Unknown benchmark_condition"):
        make_agent(tmp_path, "E")


def test_A_is_full_native_history_with_zero_memory_side_effects(tmp_path, monkeypatch):
    install_memory_bombs(monkeypatch)
    agent, model, _ = make_agent(tmp_path, "A", memory_enabled=True)
    for step in range(1, 7):
        agent.messages.extend(native_step(step))
    expected = copy.deepcopy(agent.messages)
    assert agent._memory_runtime is None
    agent.query()
    assert model.last_messages == expected
    assert not has_memory_message(model.last_messages)
    assert not (tmp_path / "condition.A.sqlite").exists()


def test_B_is_exact_last4_complete_native_steps_and_zero_memory_side_effects(tmp_path, monkeypatch):
    install_memory_bombs(monkeypatch)
    agent, model, _ = make_agent(tmp_path, "B", memory_enabled=True)
    complete = []
    for step in range(1, 7):
        group = native_step(step)
        complete.append(copy.deepcopy(group))
        agent.messages.extend(group)
    agent.messages.append({"role": "assistant", "content": "incomplete", "_verbatim_marker": "must-not-appear"})
    expected = copy.deepcopy(agent.messages[:2] + [m for group in complete[-4:] for m in group])
    assert agent._memory_runtime is None
    agent.query()
    assert model.last_messages == expected
    assert len(model.last_messages) == 10
    assert not has_memory_message(model.last_messages)
    assert not (tmp_path / "condition.B.sqlite").exists()


def test_C_and_D_activate_same_runtime_with_only_ranking_policy_different(tmp_path):
    c, _, _ = make_agent(tmp_path, "C")
    d, _, _ = make_agent(tmp_path, "D")
    assert type(c._memory_runtime) is type(d._memory_runtime)
    assert c._memory_runtime.ranking_policy == "structured"
    assert d._memory_runtime.ranking_policy == "lexical"
    assert c._memory_runtime.db_path.name == "condition.C.sqlite"
    assert d._memory_runtime.db_path.name == "condition.D.sqlite"
    assert c._memory_runtime.db_path != d._memory_runtime.db_path


def test_legacy_C_path_remains_structured_and_unscoped(tmp_path):
    model = CaptureModel()
    base = tmp_path / "legacy.sqlite"
    agent = DefaultAgent(
        model=model,
        env=FakeEnv(),
        system_template="SYS",
        instance_template="TASK",
        memory_enabled=True,
        memory_db_path=base,
        memory_task_id="t",
        memory_workspace=tmp_path,
    )
    assert agent._benchmark_condition is None
    assert agent._memory_runtime.ranking_policy == "structured"
    assert agent._memory_runtime.db_path == base


def _without_memory_id(record):
    data = asdict(record)
    data.pop("memory_id")
    return data


def test_C_and_D_store_identical_chunks_fingerprints_and_write_policy(tmp_path):
    from minisweagent.memory.store import MemoryEvent

    state_file = tmp_path / "state.txt"
    state_file.write_text("same-state", encoding="utf-8")
    c, _, _ = make_agent(tmp_path, "C", task_id="shared")
    d, _, _ = make_agent(tmp_path, "D", task_id="shared")
    event = MemoryEvent(
        task_id="shared",
        step_id=1,
        content="alpha evidence " * 60,
        kind="TOOL",
        source_ref="tool-1",
        file_paths=["state.txt"],
        command="pytest tests/x.py",
        outcome="SUCCESS",
        returncode=0,
        workspace=str(tmp_path),
    )
    c_rows = c._memory_runtime.store_event(event)
    d_rows = d._memory_runtime.store_event(event)
    assert len(c_rows) == len(d_rows) > 1
    assert [_without_memory_id(r) for r in c_rows] == [_without_memory_id(r) for r in d_rows]
    assert all(len(r.content.encode("utf-8")) <= 256 for r in c_rows + d_rows)
    assert all(r.file_fingerprints for r in c_rows + d_rows)


def test_no_cross_condition_or_cross_task_state(tmp_path):
    from minisweagent.memory.store import MemoryEvent

    c, _, _ = make_agent(tmp_path, "C", task_id="same")
    d, _, _ = make_agent(tmp_path, "D", task_id="same")
    c._memory_runtime.store_event(MemoryEvent(task_id="same", step_id=1, content="alpha", kind="TOOL"))
    with d._memory_runtime.store.connect() as con:
        assert con.execute("SELECT count(*) FROM memories").fetchone()[0] == 0

    c._memory_runtime.start_task("different task", task_id="other")
    messages = [{"role": "system", "content": "SYS"}, {"role": "user", "content": "TASK"}]
    provider_messages = c._memory_runtime.build_provider_messages(messages, current_step=10)
    assert provider_messages == messages
    assert not c._memory_runtime.last_retrieval.candidates


def test_D_is_pure_lexical_while_C_retains_exact_frozen_structured_score(tmp_path):
    from minisweagent.memory.retrieve import RetrievalState, retrieve
    from minisweagent.memory.store import MemoryEvent, MemoryStore

    db = tmp_path / "ranking.sqlite"
    store = MemoryStore(db)
    lexical = store.store(
        MemoryEvent(
            task_id="t",
            step_id=1,
            content="alpha lexical evidence",
            kind="TOOL",
            memory_type="TOOL_RESULT",
            verification_status="OBSERVED",
            importance=1,
        )
    )[0]
    structured_only = store.store(
        MemoryEvent(
            task_id="t",
            step_id=2,
            content="omega unrelated",
            kind="TOOL",
            command="make special",
            outcome="FAILED",
            memory_type="FAILED_APPROACH",
            verification_status="VERIFIED",
            importance=5,
        )
    )[0]
    state = RetrievalState(
        task_id="t",
        current_step=10,
        task_text="alpha",
        failed_command_signature="make special",
    )
    c = retrieve("alpha", state, 2048, db_path=db, ranking_policy="structured")
    d = retrieve("alpha", state, 2048, db_path=db, ranking_policy="lexical")

    def signature(meta):
        return {k: v for k, v in meta.items() if k != "score"}

    assert [signature(m) for m in c.candidates] == [signature(m) for m in d.candidates]
    verification_weight = {"VERIFIED": 1.0, "OBSERVED": 0.6, "UNVERIFIED": 0.0}
    for meta in c.candidates:
        record = store.get(meta["memory_id"])
        lexical_rr = 0.0 if meta["rank"] >= 10**6 else 1.0 / meta["rank"]
        expected = (
            lexical_rr * 1.00
            + meta["file_overlap"] * 0.35
            + meta["failure_test_match"] * 0.30
            + verification_weight[record.verification_status] * 0.15
            + record.importance * 0.10
        )
        assert meta["score"] == pytest.approx(round(expected, 6))
    for meta in d.candidates:
        lexical_rr = 0.0 if meta["rank"] >= 10**6 else 1.0 / meta["rank"]
        assert meta["score"] == pytest.approx(round(lexical_rr, 6))

    assert lexical.memory_id in {m["memory_id"] for m in d.selected}
    assert structured_only.memory_id in {m["memory_id"] for m in c.selected}
    assert structured_only.memory_id not in {m["memory_id"] for m in d.selected}


def test_C_and_D_share_identical_freshness_staleness_safety(tmp_path):
    from minisweagent.memory.retrieve import RetrievalState, retrieve
    from minisweagent.memory.store import MemoryEvent, MemoryStore

    p = tmp_path / "state.txt"
    p.write_text("before", encoding="utf-8")
    db = tmp_path / "freshness.sqlite"
    store = MemoryStore(db)
    record = store.store(
        MemoryEvent(
            task_id="t",
            step_id=1,
            content="alpha state evidence",
            kind="TOOL",
            memory_type="TOOL_RESULT",
            verification_status="OBSERVED",
            importance=1,
            file_paths=["state.txt"],
            workspace=str(tmp_path),
        )
    )[0]
    p.write_text("after", encoding="utf-8")
    state = RetrievalState(task_id="t", current_step=10, task_text="alpha", workspace=str(tmp_path))
    c = retrieve("alpha", state, 2048, db_path=db, ranking_policy="structured")
    d = retrieve("alpha", state, 2048, db_path=db, ranking_policy="lexical")
    cm = next(m for m in c.candidates if m["memory_id"] == record.memory_id)
    dm = next(m for m in d.candidates if m["memory_id"] == record.memory_id)
    assert cm["freshness"] == dm["freshness"] == "STALE"
    assert cm["excluded_current_stale_unknown"] is True
    assert dm["excluded_current_stale_unknown"] is True
    assert record.memory_id not in {m["memory_id"] for m in c.selected}
    assert record.memory_id not in {m["memory_id"] for m in d.selected}


def test_condition_neutral_settings_and_metadata_are_identical(tmp_path):
    agents = {}
    for condition in "ABCD":
        agent, model, env = make_agent(tmp_path, condition, db_name="neutral.sqlite")
        agents[condition] = (agent, model, env)

    neutral_configs = []
    for condition, (agent, model, env) in agents.items():
        config = agent.config.model_dump(mode="json")
        assert config.pop("benchmark_condition") == condition
        neutral_configs.append(config)
        assert model.config.model_dump() == agents["A"][1].config.model_dump()
        assert model.tool_schema == agents["A"][1].tool_schema
        assert type(env) is type(agents["A"][2])
        assert agent.messages[:2] == agents["A"][0].messages[:2]
        assert agent.serialize()["info"]["benchmark_condition"] == condition
    assert all(config == neutral_configs[0] for config in neutral_configs[1:])
    assert neutral_configs[0]["max_consecutive_format_errors"] == 3
    assert neutral_configs[0]["step_limit"] == 0
    assert neutral_configs[0]["cost_limit"] == 0.0
    assert neutral_configs[0]["wall_time_limit_seconds"] == 0
