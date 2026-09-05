from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess

UPSTREAM_SHA = "a83fcae82d2a08f0ee0c688f9d137b3566c097f8"
EXPECTED_BLOBS = {
    "pyproject.toml": "0bd3e1329252af4399805959d78d5984f2bbf2b0",
    "src/minisweagent/__init__.py": "8dbc904c36c3ed31b3c7d9697e44dbf0cf6c0e87",
    "src/minisweagent/agents/default.py": "ca310e37d7c61888c576f73f5e1790ac769407b1",
    "src/minisweagent/models/litellm_model.py": "84b5d548df0e10cbe820862399379bbde69a6fa8",
    "src/minisweagent/models/utils/retry.py": "055d4b6fd4f57c1420dfa7622a8fe24148354548",
    "src/minisweagent/models/utils/actions_toolcall.py": "8209113c4a1663d34468be6106b5661ec9e0be62",
}


def _git(upstream: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(upstream), *args], text=True).strip()


def _replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Patch anchor {label!r} expected once, found {count}")
    return text.replace(old, new, 1)


def verify_upstream(upstream: Path) -> None:
    head = _git(upstream, "rev-parse", "HEAD")
    if head != UPSTREAM_SHA:
        raise RuntimeError(f"Wrong upstream HEAD: {head}")
    for rel, expected in EXPECTED_BLOBS.items():
        actual = _git(upstream, "hash-object", rel)
        if actual != expected:
            raise RuntimeError(f"Unexpected upstream blob for {rel}: {actual} != {expected}")
    init_text = (upstream / "src/minisweagent/__init__.py").read_text(encoding="utf-8")
    if '__version__ = "2.4.6"' not in init_text:
        raise RuntimeError("Upstream version is not 2.4.6")


def copy_cleared_modules(repo_root: Path, upstream: Path) -> None:
    staging_root = repo_root / "implementation/staging/src/minisweagent"
    destination = upstream / "src/minisweagent"
    shutil.copytree(staging_root / "memory", destination / "memory", dirs_exist_ok=True)
    shutil.copytree(staging_root / "instrumentation", destination / "instrumentation", dirs_exist_ok=True)
    overlay = repo_root / "implementation/authoritative/overlay/src/minisweagent"
    shutil.copy2(overlay / "memory/integration.py", destination / "memory/integration.py")
    shutil.copy2(
        overlay / "instrumentation/attempt_accounting.py",
        destination / "instrumentation/attempt_accounting.py",
    )


def patch_agent(upstream: Path) -> None:
    path = upstream / "src/minisweagent/agents/default.py"
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        '    output_path: Path | None = None\n    """Save the trajectory to this path."""\n',
        '    output_path: Path | None = None\n    """Save the trajectory to this path."""\n'
        '    memory_enabled: bool = False\n'
        '    """Enable the experimental task-local memory path."""\n'
        '    memory_db_path: Path | None = None\n'
        '    """Per-task SQLite memory path. Required when memory is enabled."""\n'
        '    memory_task_id: str | None = None\n'
        '    """Explicit task-local memory identity; otherwise derived from task text."""\n'
        '    memory_workspace: Path | None = None\n'
        '    """Workspace root used only for memory file freshness checks."""\n',
        label="AgentConfig memory fields",
    )
    text = _replace_once(
        text,
        "        self._start_time = time.time()\n",
        "        self._start_time = time.time()\n"
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
        label="DefaultAgent hard-bypass initialization",
    )
    text = _replace_once(
        text,
        '        self.extra_template_vars |= {"task": task, **kwargs}\n        self.messages = []\n',
        '        self.extra_template_vars |= {"task": task, **kwargs}\n'
        '        if self._memory_runtime is not None:\n'
        '            self._memory_runtime.start_task(task, task_id=self.config.memory_task_id or kwargs.get("task_id"))\n'
        '        if hasattr(self.model, "set_accounting_context"):\n'
        '            effective_task_id = (\n'
        '                self._memory_runtime.task_id if self._memory_runtime is not None else kwargs.get("task_id")\n'
        '            )\n'
        '            self.model.set_accounting_context(task_id=effective_task_id, run_id=kwargs.get("run_id"))\n'
        '        self.messages = []\n',
        label="run task initialization",
    )
    text = _replace_once(
        text,
        "            except FormatError as e:\n                # The call was billed before parsing failed, so query() never got to charge it.\n",
        "            except FormatError as e:\n"
        "                if hasattr(self.model, 'mark_next_attempt_retry'):\n"
        "                    self.model.mark_next_attempt_retry('action_parse_failure')\n"
        "                # The call was billed before parsing failed, so query() never got to charge it.\n",
        label="parse retry accounting marker",
    )
    text = _replace_once(
        text,
        "        self.n_calls += 1\n        message = self.model.query(self.messages)\n",
        "        self.n_calls += 1\n"
        "        query_messages = self.messages\n"
        "        if self._memory_runtime is not None:\n"
        "            query_messages = self._memory_runtime.build_provider_messages(\n"
        "                self.messages, current_step=self.n_calls\n"
        "            )\n"
        "        message = self.model.query(query_messages)\n",
        label="hard native query bypass",
    )
    text = _replace_once(
        text,
        '        outputs = [self.env.execute(action) for action in message.get("extra", {}).get("actions", [])]\n'
        '        return self.add_messages(*self.model.format_observation_messages(message, outputs, self.get_template_vars()))\n',
        '        outputs = [self.env.execute(action) for action in message.get("extra", {}).get("actions", [])]\n'
        '        observations = self.model.format_observation_messages(message, outputs, self.get_template_vars())\n'
        '        added = self.add_messages(*observations)\n'
        '        if self._memory_runtime is not None:\n'
        '            self._memory_runtime.ingest_step(message, added, outputs, step_id=self.n_calls)\n'
        '        return added\n',
        label="memory write hook",
    )
    path.write_text(text, encoding="utf-8")


def patch_litellm_model(upstream: Path) -> None:
    path = upstream / "src/minisweagent/models/litellm_model.py"
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        "from minisweagent.exceptions import FormatError\n",
        "from minisweagent.exceptions import FormatError\n"
        "from minisweagent.instrumentation.attempt_accounting import AttemptLedger\n",
        label="accounting import",
    )
    text = _replace_once(
        text,
        "    def __init__(self, *, config_class: Callable = LitellmModelConfig, **kwargs):\n"
        "        self.config = config_class(**kwargs)\n"
        "        if self.config.litellm_model_registry and Path(self.config.litellm_model_registry).is_file():\n"
        "            litellm.utils.register_model(json.loads(Path(self.config.litellm_model_registry).read_text()))\n\n"
        "    def _query(self, messages: list[dict[str, str]], **kwargs):\n",
        "    def __init__(self, *, config_class: Callable = LitellmModelConfig, **kwargs):\n"
        "        self.config = config_class(**kwargs)\n"
        "        if self.config.litellm_model_registry and Path(self.config.litellm_model_registry).is_file():\n"
        "            litellm.utils.register_model(json.loads(Path(self.config.litellm_model_registry).read_text()))\n"
        "        self.attempt_ledger = AttemptLedger.from_env()\n"
        "        self._pending_retry_reason: str | None = None\n\n"
        "    def set_accounting_context(self, *, task_id: str | None = None, run_id: str | None = None) -> None:\n"
        "        self.attempt_ledger.set_context(task_id=task_id, run_id=run_id)\n\n"
        "    def mark_next_attempt_retry(self, reason: str) -> None:\n"
        "        self._pending_retry_reason = reason\n\n"
        "    def _query(self, messages: list[dict[str, str]], **kwargs):\n",
        label="ledger initialization",
    )
    old_query = '''    def query(self, messages: list[dict[str, str]], **kwargs) -> dict:\n        for attempt in retry(logger=logger, abort_exceptions=self.abort_exceptions):\n            with attempt:\n                response = self._query(self._prepare_messages_for_api(messages), **kwargs)\n        cost_output = self._calculate_cost(response)\n        GLOBAL_MODEL_STATS.add(cost_output["cost"])\n        # Note: all model.query() implementations must persist the response and cost on FormatError.\n        try:\n            actions = self._parse_actions(response)\n        except FormatError as e:\n            e.messages[0]["extra"].update(cost_output)\n            try:\n                e.messages[0]["extra"]["response"] = response.model_dump(mode="json")\n            except Exception:\n                # model_dump failed (e.g. unserializable object); fall back to repr\n                # so the spec contract ("response MUST be persisted") holds unconditionally.\n                e.messages[0]["extra"]["response"] = repr(response)\n            raise\n        message = response.choices[0].message.model_dump()\n        message["extra"] = {\n            "actions": actions,\n            "response": response.model_dump(),\n            **cost_output,\n            "timestamp": time.time(),\n        }\n        return message\n'''
    new_query = '''    def query(self, messages: list[dict[str, str]], **kwargs) -> dict:\n        prepared_messages = self._prepare_messages_for_api(messages)\n        response = None\n        final_attempt_id: str | None = None\n        for retry_index, attempt in enumerate(retry(logger=logger, abort_exceptions=self.abort_exceptions)):\n            retry_reason = self._pending_retry_reason if retry_index == 0 else "provider_retry"\n            is_retry = retry_index > 0 or retry_reason is not None\n            record = self.attempt_ledger.begin(\n                retry_index=retry_index, retry=is_retry, retry_reason=retry_reason\n            )\n            if retry_index == 0:\n                self._pending_retry_reason = None\n            with attempt:\n                try:\n                    response = self._query(prepared_messages, **kwargs)\n                except BaseException as error:\n                    self.attempt_ledger.record_provider_error(record.attempt_id, error)\n                    raise\n                else:\n                    # Capture provider usage immediately after response receipt, before cost/action parsing.\n                    self.attempt_ledger.record_response(record.attempt_id, response)\n                    final_attempt_id = record.attempt_id\n        cost_output = self._calculate_cost(response)\n        GLOBAL_MODEL_STATS.add(cost_output["cost"])\n        # Note: all model.query() implementations must persist the response and cost on FormatError.\n        try:\n            actions = self._parse_actions(response)\n        except FormatError as e:\n            self.attempt_ledger.record_parse(final_attempt_id, False)\n            self._pending_retry_reason = "action_parse_failure"\n            e.messages[0]["extra"].update(cost_output)\n            try:\n                e.messages[0]["extra"]["response"] = response.model_dump(mode="json")\n            except Exception:\n                # model_dump failed (e.g. unserializable object); fall back to repr\n                # so the spec contract ("response MUST be persisted") holds unconditionally.\n                e.messages[0]["extra"]["response"] = repr(response)\n            raise\n        self.attempt_ledger.record_parse(final_attempt_id, True)\n        message = response.choices[0].message.model_dump()\n        message["extra"] = {\n            "actions": actions,\n            "response": response.model_dump(),\n            "provider_attempt_id": final_attempt_id,\n            **cost_output,\n            "timestamp": time.time(),\n        }\n        return message\n'''
    text = _replace_once(text, old_query, new_query, label="provider attempt boundary")
    text = _replace_once(
        text,
        '    def serialize(self) -> dict:\n        return {\n            "info": {\n                "config": {\n                    "model": self.config.model_dump(mode="json"),\n                    "model_type": f"{self.__class__.__module__}.{self.__class__.__name__}",\n                },\n            }\n        }\n',
        '    def serialize(self) -> dict:\n'
        '        return {\n'
        '            "info": {\n'
        '                "config": {\n'
        '                    "model": self.config.model_dump(mode="json"),\n'
        '                    "model_type": f"{self.__class__.__module__}.{self.__class__.__name__}",\n'
        '                },\n'
        '                "provider_attempts": self.attempt_ledger.snapshot(),\n'
        '                "provider_accounting": self.attempt_ledger.aggregate(),\n'
        '            }\n'
        '        }\n',
        label="trajectory attempt preservation",
    )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    upstream = args.upstream.resolve()
    verify_upstream(upstream)
    copy_cleared_modules(repo_root, upstream)
    patch_agent(upstream)
    patch_litellm_model(upstream)
    print(f"UPSTREAM_BASE_SHA={UPSTREAM_SHA}")
    print("INTEGRATION_APPLIED=YES")


if __name__ == "__main__":
    main()
