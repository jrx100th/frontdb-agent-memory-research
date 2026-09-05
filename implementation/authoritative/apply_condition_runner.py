from __future__ import annotations

import argparse
from pathlib import Path


def _replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Condition-runner patch anchor {label!r} expected once, found {count}")
    return text.replace(old, new, 1)


def patch_agent(upstream: Path) -> None:
    path = upstream / "src/minisweagent/agents/default.py"
    text = path.read_text(encoding="utf-8")

    helper_block = '''\n\nBENCHMARK_CONDITIONS = frozenset({"A", "B", "C", "D"})\n\n\ndef _validate_benchmark_condition(value: str | None) -> str | None:\n    if value is None:\n        return None\n    if value not in BENCHMARK_CONDITIONS:\n        raise ValueError(f"Unknown benchmark_condition: {value!r}; expected one of A/B/C/D")\n    return value\n\n\ndef _condition_scoped_db_path(path: Path, condition: str) -> Path:\n    suffix = path.suffix\n    stem = path.name[:-len(suffix)] if suffix else path.name\n    return path.with_name(f"{stem}.{condition}{suffix}")\n\n\ndef _last4_complete_native_messages(messages: list[dict]) -> list[dict]:\n    """Return system + original task + last four complete native steps verbatim."""\n    if len(messages) < 2:\n        return list(messages)\n    groups: list[list[dict]] = []\n    current: list[dict] | None = None\n    for message in messages[2:]:\n        if message.get("role") == "assistant":\n            if current and len(current) > 1:\n                groups.append(current)\n            current = [message]\n        elif current is not None:\n            current.append(message)\n    if current and len(current) > 1:\n        groups.append(current)\n    out = [messages[0], messages[1]]\n    for group in groups[-4:]:\n        out.extend(group)\n    return out\n'''
    text = _replace_once(
        text,
        "\n\nclass AgentConfig(BaseModel):\n",
        helper_block + "\n\nclass AgentConfig(BaseModel):\n",
        label="condition helper insertion",
    )
    text = _replace_once(
        text,
        '    memory_workspace: Path | None = None\n    """Workspace root used only for memory file freshness checks."""\n',
        '    memory_workspace: Path | None = None\n'
        '    """Workspace root used only for memory file freshness checks."""\n'
        '    benchmark_condition: str | None = None\n'
        '    """Explicit reproducibility condition selector: A, B, C, or D."""\n',
        label="AgentConfig benchmark condition",
    )
    text = _replace_once(
        text,
        "        self._memory_runtime = None\n"
        "        if self.config.memory_enabled:\n"
        "            if self.config.memory_db_path is None:\n"
        "                raise ValueError('memory_db_path is required when memory_enabled=true')\n"
        "            from minisweagent.memory.integration import MemoryRuntime\n"
        "\n"
        "            self._memory_runtime = MemoryRuntime(\n"
        "                db_path=self.config.memory_db_path,\n"
        "                workspace=self.config.memory_workspace,\n"
        "                configured_task_id=self.config.memory_task_id,\n"
        "            )\n",
        "        self._benchmark_condition = _validate_benchmark_condition(self.config.benchmark_condition)\n"
        "        self._memory_runtime = None\n"
        "        memory_active = (\n"
        "            self.config.memory_enabled\n"
        "            if self._benchmark_condition is None\n"
        "            else self._benchmark_condition in {'C', 'D'}\n"
        "        )\n"
        "        if memory_active:\n"
        "            if self.config.memory_db_path is None:\n"
        "                raise ValueError('memory_db_path is required when structured/lexical memory is active')\n"
        "            from minisweagent.memory.integration import MemoryRuntime\n"
        "\n"
        "            db_path = self.config.memory_db_path\n"
        "            ranking_policy = 'structured'\n"
        "            if self._benchmark_condition in {'C', 'D'}:\n"
        "                db_path = _condition_scoped_db_path(db_path, self._benchmark_condition)\n"
        "                ranking_policy = 'lexical' if self._benchmark_condition == 'D' else 'structured'\n"
        "            self._memory_runtime = MemoryRuntime(\n"
        "                db_path=db_path,\n"
        "                workspace=self.config.memory_workspace,\n"
        "                configured_task_id=self.config.memory_task_id,\n"
        "                ranking_policy=ranking_policy,\n"
        "            )\n",
        label="condition-aware runtime initialization",
    )
    text = _replace_once(
        text,
        "        query_messages = self.messages\n"
        "        if self._memory_runtime is not None:\n"
        "            query_messages = self._memory_runtime.build_provider_messages(\n"
        "                self.messages, current_step=self.n_calls\n"
        "            )\n",
        "        query_messages = self.messages\n"
        "        if self._benchmark_condition == 'B':\n"
        "            query_messages = _last4_complete_native_messages(self.messages)\n"
        "        elif self._memory_runtime is not None:\n"
        "            query_messages = self._memory_runtime.build_provider_messages(\n"
        "                self.messages, current_step=self.n_calls\n"
        "            )\n",
        label="condition-aware provider context",
    )
    text = _replace_once(
        text,
        '                "mini_version": __version__,\n',
        '                "mini_version": __version__,\n'
        '                "benchmark_condition": self._benchmark_condition,\n',
        label="condition metadata",
    )
    path.write_text(text, encoding="utf-8")


def patch_runtime(upstream: Path) -> None:
    path = upstream / "src/minisweagent/memory/integration.py"
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        "        configured_task_id: str | None = None,\n"
        "    ):\n"
        "        self.db_path = Path(db_path)\n",
        "        configured_task_id: str | None = None,\n"
        "        ranking_policy: str = 'structured',\n"
        "    ):\n"
        "        if ranking_policy not in {'structured', 'lexical'}:\n"
        "            raise ValueError(f'Unknown ranking_policy: {ranking_policy!r}')\n"
        "        self.ranking_policy = ranking_policy\n"
        "        self.db_path = Path(db_path)\n",
        label="runtime ranking policy",
    )
    text = _replace_once(
        text,
        "        result = retrieve(query, state, RETRIEVAL_BUDGET, db_path=self.db_path)\n",
        "        result = retrieve(\n"
        "            query, state, RETRIEVAL_BUDGET, db_path=self.db_path, ranking_policy=self.ranking_policy\n"
        "        )\n",
        label="runtime retrieval policy wiring",
    )
    path.write_text(text, encoding="utf-8")


def patch_retriever(upstream: Path) -> None:
    path = upstream / "src/minisweagent/memory/retrieve.py"
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        "def retrieve(query: str, state: RetrievalState, budget_tokens: int, *, db_path: str | Path) -> RetrievalResult:\n"
        "    budget = min(RETRIEVAL_BUDGET, max(0, int(budget_tokens)))\n",
        "def retrieve(\n"
        "    query: str,\n"
        "    state: RetrievalState,\n"
        "    budget_tokens: int,\n"
        "    *,\n"
        "    db_path: str | Path,\n"
        "    ranking_policy: str = 'structured',\n"
        ") -> RetrievalResult:\n"
        "    if ranking_policy not in {'structured', 'lexical'}:\n"
        "        raise ValueError(f'Unknown ranking_policy: {ranking_policy!r}')\n"
        "    budget = min(RETRIEVAL_BUDGET, max(0, int(budget_tokens)))\n",
        label="retriever ranking policy argument",
    )
    frozen_score = (
        "        score = lexical_rr * 1.00 + file_overlap * 0.35 + failure_test_match * 0.30 + "
        "EVIDENCE.get(rec.verification_status, 0.0) * 0.15 + rec.importance * 0.10\n"
    )
    text = _replace_once(
        text,
        frozen_score,
        "        if ranking_policy == 'structured':\n"
        + frozen_score.replace("        score", "            score")
        + "        else:\n"
        "            score = lexical_rr\n",
        label="structured versus lexical score",
    )
    text = _replace_once(
        text,
        "    for score, rec, freshness, meta in deduped:\n"
        "        if len(selected_records) >= MAX_SELECTED:\n",
        "    for score, rec, freshness, meta in deduped:\n"
        "        if ranking_policy == 'lexical' and score <= 0.0:\n"
        "            continue\n"
        "        if len(selected_records) >= MAX_SELECTED:\n",
        label="lexical-only selection gate",
    )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    args = parser.parse_args()
    upstream = args.upstream.resolve()
    patch_agent(upstream)
    patch_runtime(upstream)
    patch_retriever(upstream)
    print("CONDITION_RUNNER_APPLIED=YES")
    print("CONDITIONS=A,B,C,D")
    print("FROZEN_C_CONSTANTS_CHANGED=NO")


if __name__ == "__main__":
    main()
