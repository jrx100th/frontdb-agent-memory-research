from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import hashlib
import time

from .context_builder import build_context, group_complete_steps
from .retrieve import RETRIEVAL_BUDGET, RetrievalState, retrieve
from .store import MemoryEvent, MemoryStore

RECENT_STEPS = 4


@dataclass
class MemoryTelemetry:
    db_initializations: int = 0
    db_reads: int = 0
    db_writes: int = 0
    retrieval_calls: int = 0
    context_calls: int = 0
    synthetic_messages: int = 0
    candidate_ids: list[int] = field(default_factory=list)
    selected_ids: list[int] = field(default_factory=list)
    freshness: dict[int, str] = field(default_factory=dict)
    fingerprint_files: list[str] = field(default_factory=list)
    message_local_units: int = 0
    retrieval_latency_seconds: float = 0.0
    db_size_bytes: int = 0


def construct_condition_messages(condition: str, native_messages: list[dict], retrieved=None) -> list[dict]:
    if condition == "native":
        return native_messages
    if len(native_messages) < 2:
        return list(native_messages)
    system, task = native_messages[0], native_messages[1]
    history = native_messages[2:]
    if condition == "last4":
        return build_context(system, task, history, None)
    if condition == "memory":
        return build_context(system, task, history, retrieved)
    raise ValueError(f"Unknown condition: {condition}")


def _message_text(message: dict) -> str:
    parts: list[str] = []
    content = message.get("content")
    if isinstance(content, str) and content:
        parts.append(content)
    extra = message.get("extra") or {}
    raw = extra.get("raw_output")
    if isinstance(raw, str) and raw and raw not in parts:
        parts.append(raw)
    for action in extra.get("actions", []) or []:
        command = action.get("command") if isinstance(action, dict) else None
        if isinstance(command, str) and command:
            parts.append(command)
    return "\n".join(parts)


def _latest_failed_command(groups: list[list[dict]]) -> str | None:
    if not groups:
        return None
    group = groups[-1]
    assistant = group[0] if group and group[0].get("role") == "assistant" else {}
    actions = (assistant.get("extra") or {}).get("actions", []) or []
    observations = [m for m in group[1:] if m.get("role") in {"tool", "user"}]
    for action, observation in reversed(list(zip(actions, observations))):
        rc = (observation.get("extra") or {}).get("returncode")
        if rc not in (None, 0):
            command = action.get("command") if isinstance(action, dict) else None
            if isinstance(command, str) and command:
                return command
    return None


class MemoryRuntime:
    def __init__(
        self,
        *,
        db_path: str | Path,
        workspace: str | Path | None = None,
        configured_task_id: str | None = None,
    ):
        self.db_path = Path(db_path)
        self.workspace = str(workspace) if workspace is not None else None
        self.configured_task_id = configured_task_id
        self.task_id: str | None = configured_task_id
        self.task_text = ""
        self.store = MemoryStore(self.db_path)
        self.telemetry = MemoryTelemetry(db_initializations=1)
        self.last_retrieval = None
        self._update_db_size()

    def start_task(self, task: str, *, task_id: str | None = None) -> None:
        self.task_text = task
        explicit = task_id or self.configured_task_id
        self.task_id = explicit or hashlib.sha256(task.encode("utf-8")).hexdigest()

    def store_event(self, event: MemoryEvent | dict[str, Any]):
        if self.task_id is None:
            raise RuntimeError("Memory task not initialized")
        if isinstance(event, dict):
            event = MemoryEvent(**event)
        if event.task_id != self.task_id:
            raise ValueError("Cross-task memory write rejected")
        created = self.store.store(event)
        self.telemetry.db_writes += len(created)
        self.telemetry.fingerprint_files.extend(str(p) for p in event.file_paths)
        self._update_db_size()
        return created

    def ingest_step(self, assistant: dict, observations: list[dict], outputs: list[dict], *, step_id: int) -> None:
        if self.task_id is None:
            raise RuntimeError("Memory task not initialized")
        assistant_content = assistant.get("content")
        if isinstance(assistant_content, str) and assistant_content:
            self.store_event(
                MemoryEvent(
                    task_id=self.task_id,
                    step_id=step_id,
                    content=assistant_content,
                    kind="ASSISTANT",
                    source_ref="assistant",
                )
            )
        actions = (assistant.get("extra") or {}).get("actions", []) or []
        for index, observation in enumerate(observations):
            extra = observation.get("extra") or {}
            output = outputs[index] if index < len(outputs) else {}
            raw = extra.get("raw_output")
            content = raw if isinstance(raw, str) and raw else str(observation.get("content") or "")
            action = actions[index] if index < len(actions) and isinstance(actions[index], dict) else {}
            command = action.get("command")
            returncode = extra.get("returncode", output.get("returncode"))
            outcome = "FAILED" if returncode not in (None, 0) else "SUCCESS"
            self.store_event(
                MemoryEvent(
                    task_id=self.task_id,
                    step_id=step_id,
                    content=content,
                    kind="TOOL",
                    source_ref=observation.get("tool_call_id"),
                    command=command,
                    outcome=outcome,
                    returncode=returncode,
                    workspace=self.workspace,
                )
            )

    def build_provider_messages(self, native_messages: list[dict], *, current_step: int) -> list[dict]:
        if self.task_id is None:
            raise RuntimeError("Memory task not initialized")
        history = native_messages[2:] if len(native_messages) >= 2 else []
        groups = group_complete_steps(history)
        latest = groups[-1] if groups else []
        query = "\n".join(filter(None, (_message_text(message) for message in latest))).strip()
        if not query:
            query = self.task_text
        failed_command = _latest_failed_command(groups)
        state = RetrievalState(
            task_id=self.task_id,
            current_step=current_step,
            workspace=self.workspace,
            task_text=self.task_text,
            failed_command_signature=failed_command,
        )
        started = time.perf_counter()
        result = retrieve(query, state, RETRIEVAL_BUDGET, db_path=self.db_path)
        latency = time.perf_counter() - started
        self.last_retrieval = result
        self.telemetry.db_reads += 1
        self.telemetry.retrieval_calls += 1
        self.telemetry.context_calls += 1
        self.telemetry.retrieval_latency_seconds = latency
        self.telemetry.candidate_ids = [int(item["memory_id"]) for item in result.candidates]
        self.telemetry.selected_ids = [int(item["memory_id"]) for item in result.selected]
        self.telemetry.freshness = {int(item["memory_id"]): str(item.get("freshness")) for item in result.candidates}
        self.telemetry.message_local_units = int(result.serialized_memory_units)
        fingerprint_paths: list[str] = []
        for record in result.serialized_records:
            fingerprint_paths.extend(str(p) for p in record.get("file_paths", []))
        self.telemetry.fingerprint_files.extend(fingerprint_paths)
        if result.serialized_records:
            self.telemetry.synthetic_messages += 1
        self._update_db_size()
        return construct_condition_messages("memory", native_messages, result)

    def telemetry_snapshot(self) -> dict:
        return asdict(self.telemetry)

    def _update_db_size(self) -> None:
        try:
            self.telemetry.db_size_bytes = self.db_path.stat().st_size
        except (FileNotFoundError, AttributeError):
            if hasattr(self, "telemetry"):
                self.telemetry.db_size_bytes = 0
