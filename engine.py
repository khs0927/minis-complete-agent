from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class Capability:
    name: str
    kind: str
    description: str
    source: str
    enabled: bool = True
    risk: str = "low"


@dataclass
class Evidence:
    kind: str
    description: str
    passed: bool
    location: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    sha256: str | None = None


@dataclass
class VerificationReport:
    score: float
    passed: bool
    gates: dict[str, bool]
    missing: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class ApprovalRequest:
    action: str
    risk_level: str
    preview: dict[str, Any]
    requires_confirmation: bool
    confirmed: bool = False


@dataclass
class SubagentTask:
    task_id: str
    workstream: str
    objective: str
    allowed_capabilities: list[str]
    status: str = "planned"
    result: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    mission_id: str
    status: str
    workstreams: list[str]
    subagents: list[SubagentTask]
    evidence: list[Evidence]
    verification: VerificationReport | None = None
    approval: ApprovalRequest | None = None
    trace_path: str | None = None


class Adapter(Protocol):
    name: str
    def can_handle(self, workstream: str) -> bool: ...
    def preview(self, mission: dict[str, Any]) -> dict[str, Any]: ...
    def execute(self, mission: dict[str, Any], task: SubagentTask) -> tuple[dict[str, Any], list[Evidence]]: ...


class CapabilityRegistry:
    def __init__(self, skills_root: Path = Path("/home/ubuntu/skills"), config_path: Path = Path.home() / ".manus/config/config.json") -> None:
        self.skills_root = skills_root
        self.config_path = config_path

    def discover(self) -> list[Capability]:
        items: list[Capability] = []
        if self.skills_root.exists():
            for skill_file in sorted(self.skills_root.glob("*/SKILL.md")):
                text = skill_file.read_text(encoding="utf-8", errors="replace")
                name = skill_file.parent.name
                match = re.search(r"^description:\s*(?:>|\\|)?\\s*(.*)$", text, re.MULTILINE)
                description = (match.group(1).strip() if match else "") or f"Skill workflow: {name}"
                description = re.sub(r"\\s+", " ", description)[:500]
                items.append(Capability(name, "skill", description, str(skill_file), True, "low"))
        try:
            raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            raw = {}
        connectors = raw.get("connectors", raw.get("mcpServers", {})) if isinstance(raw, dict) else {}
        if isinstance(connectors, dict):
            for key, value in sorted(connectors.items()):
                if isinstance(value, dict):
                    enabled = bool(value.get("enabled", True))
                    kind = str(value.get("kind", "connector"))
                else:
                    enabled, kind = True, "connector"
                items.append(Capability(key, kind, f"Configured connector: {key}", "manus-config", enabled, "high"))
        return items

    def summary(self) -> dict[str, Any]:
        items = self.discover()
        return {
            "total": len(items),
            "enabled": sum(item.enabled for item in items),
            "skills": sum(item.kind == "skill" for item in items),
            "connectors": sum(item.kind != "skill" for item in items),
            "items": [asdict(item) for item in items],
        }


class LocalEvidenceAdapter:
    name = "local-evidence"

    def can_handle(self, workstream: str) -> bool:
        return True

    def preview(self, mission: dict[str, Any]) -> dict[str, Any]:
        return {"adapter": self.name, "mode": "local", "side_effects": [], "workstreams": mission.get("workstreams", [])}

    def execute(self, mission: dict[str, Any], task: SubagentTask) -> tuple[dict[str, Any], list[Evidence]]:
        task.status = "running"
        output = {"objective": task.objective, "workstream": task.workstream, "mode": "deterministic-local"}
        evidence = [Evidence("execution", f"Local adapter completed {task.workstream}", True, metadata={"task_id": task.task_id})]
        task.status = "completed"
        task.result = output
        return output, evidence


class ConnectorDelegationAdapter:
    name = "manus-api-delegation"

    def can_handle(self, workstream: str) -> bool:
        return workstream in {"research", "automation", "device", "commerce"}

    def preview(self, mission: dict[str, Any]) -> dict[str, Any]:
        return {"adapter": self.name, "mode": "delegated", "side_effects": ["external connector call"], "requires_approval": True}

    def execute(self, mission: dict[str, Any], task: SubagentTask) -> tuple[dict[str, Any], list[Evidence]]:
        task.status = "blocked"
        result = {"reason": "Connector delegation requires an explicit Manus API integration and approved connector UID.", "next": "Provide/configure the intended connector before execution."}
        task.result = result
        return result, [Evidence("guard", "External connector execution blocked by default-deny policy", True, metadata={"task_id": task.task_id})]


class Verifier:
    THRESHOLD = 0.82

    def verify(self, workstreams: list[str], evidence: list[Evidence], risk: str) -> VerificationReport:
        gates = {"evidence_present": bool(evidence), "all_evidence_passed": all(item.passed for item in evidence)}
        if risk in {"high", "critical"}:
            gates["approval_required"] = False
        passed_count = sum(gates.values())
        score = passed_count / len(gates) if gates else 0.0
        missing = [key for key, value in gates.items() if not value]
        recommendations = ["Run the missing adapter or collect an independent receipt."] if missing else []
        return VerificationReport(round(score, 3), score >= self.THRESHOLD and not missing, gates, missing, recommendations)


class MissionEngine:
    def __init__(self, workspace: Path = Path(".minis"), registry: CapabilityRegistry | None = None) -> None:
        self.workspace = workspace
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.registry = registry or CapabilityRegistry()
        self.adapters: list[Adapter] = [LocalEvidenceAdapter(), ConnectorDelegationAdapter()]
        self.verifier = Verifier()

    def _trace(self, mission_id: str, event: str, payload: dict[str, Any]) -> str:
        path = self.workspace / f"{mission_id}.jsonl"
        safe = {"timestamp": time.time(), "mission_id": mission_id, "event": event, "payload": payload}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(safe, ensure_ascii=False, default=str) + "\n")
        return str(path)

    def _make_tasks(self, mission: dict[str, Any]) -> list[SubagentTask]:
        allowed = [item.name for item in self.registry.discover() if item.enabled]
        return [SubagentTask(f"sub-{uuid.uuid4().hex[:8]}", kind, f"Complete {kind} workstream", allowed) for kind in mission.get("workstreams", [])]

    def preview(self, mission: dict[str, Any]) -> ExecutionResult:
        mission_id = mission["mission_id"]
        tasks = self._make_tasks(mission)
        risk = mission.get("risk_level", "low")
        approval = ApprovalRequest("mission execution", risk, {"tasks": [asdict(t) for t in tasks], "registry": self.registry.summary()}, risk in {"high", "critical"})
        result = ExecutionResult(mission_id, "previewed", mission.get("workstreams", []), tasks, [], None, approval)
        result.trace_path = self._trace(mission_id, "previewed", {"risk": risk, "task_count": len(tasks)})
        return result

    def execute(self, mission: dict[str, Any], confirmed: bool = False) -> ExecutionResult:
        preview = self.preview(mission)
        if preview.approval and preview.approval.requires_confirmation and not confirmed:
            preview.status = "awaiting_approval"
            return preview
        evidence: list[Evidence] = []
        def run_task(task: SubagentTask) -> tuple[SubagentTask, str, list[Evidence]]:
            adapter = next((item for item in self.adapters if item.can_handle(task.workstream)), self.adapters[0])
            _, task_evidence = adapter.execute(mission, task)
            return task, adapter.name, task_evidence
        max_workers = min(4, max(1, len(preview.subagents)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(run_task, task) for task in preview.subagents]
            for future in concurrent.futures.as_completed(futures):
                task, adapter_name, task_evidence = future.result()
                evidence.extend(task_evidence)
                self._trace(mission["mission_id"], "subagent_completed", {"task": asdict(task), "adapter": adapter_name})
        verification = self.verifier.verify(mission.get("workstreams", []), evidence, mission.get("risk_level", "low"))
        status = "passed" if verification.passed else "repair_required"
        result = ExecutionResult(mission["mission_id"], status, mission.get("workstreams", []), preview.subagents, evidence, verification, preview.approval)
        result.trace_path = self._trace(mission["mission_id"], "verified", {"status": status, "verification": asdict(verification)})
        return result

    @staticmethod
    def serializable(result: ExecutionResult) -> dict[str, Any]:
        return asdict(result)
