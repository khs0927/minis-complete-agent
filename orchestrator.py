#!/usr/bin/env python3
"""Evidence-gated mission planner for Minis Complete Agent."""
from __future__ import annotations

import json
import sys
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


class WorkstreamKind(str, Enum):
    RESEARCH = "research"
    CODE = "code"
    DOCUMENT = "document"
    CREATIVE_MEDIA = "creative_media"
    DATA = "data"
    AUTOMATION = "automation"
    DEVICE = "device"
    COMMERCE = "commerce"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MissionPlan:
    mission_id: str
    user_request: str
    workstreams: list[str] = field(default_factory=list)
    risk_level: str = RiskLevel.LOW.value
    selected_plugins: list[str] = field(default_factory=list)
    selected_models: list[str] = field(default_factory=list)
    evidence_gates: dict[str, list[str]] = field(default_factory=dict)


class Orchestrator:
    """Plan missions using deterministic, inspectable routing rules."""

    KEYWORDS: dict[WorkstreamKind, tuple[str, ...]] = {
        WorkstreamKind.RESEARCH: ("research", "검색", "조사", "논문", "뉴스", "자료"),
        WorkstreamKind.CODE: ("code", "build", "fix", "bug", "개발", "코드", "버그", "구현"),
        WorkstreamKind.DOCUMENT: ("report", "document", "write", "보고서", "문서", "작성"),
        WorkstreamKind.CREATIVE_MEDIA: ("image", "video", "music", "이미지", "영상", "음악"),
        WorkstreamKind.DATA: ("data", "csv", "excel", "분석", "데이터", "스프레드시트"),
        WorkstreamKind.AUTOMATION: ("automate", "schedule", "sync", "자동화", "예약", "동기화"),
        WorkstreamKind.DEVICE: ("iphone", "ios", "health", "아이폰", "단축어", "건강"),
        WorkstreamKind.COMMERCE: ("buy", "sell", "pay", "purchase", "구매", "결제", "판매"),
    }

    def __init__(self) -> None:
        self.plugins = self._discover_plugins()
        self.mcp_servers = self._discover_mcp_servers()

    def status(self) -> dict:
        return {"plugins": self.plugins, "mcp_servers": self.mcp_servers}

    def _discover_plugins(self) -> dict[str, int]:
        return {"skills": 73, "apple_tools": 20, "mcp_tools": 100}

    def _discover_mcp_servers(self) -> dict[str, str]:
        return {"hermes": "stdio", "complete-agent": "stdio", "khs0927": "http"}

    def _classify(self, request: str) -> list[WorkstreamKind]:
        text = request.casefold()
        matches = [kind for kind, words in self.KEYWORDS.items() if any(word in text for word in words)]
        return matches or [WorkstreamKind.CODE]

    def _risk(self, request: str, kinds: list[WorkstreamKind]) -> RiskLevel:
        text = request.casefold()
        if any(word in text for word in ("delete", "send money", "결제", "송금", "삭제", "publish", "게시")):
            return RiskLevel.CRITICAL
        if WorkstreamKind.COMMERCE in kinds or WorkstreamKind.DEVICE in kinds:
            return RiskLevel.HIGH
        if len(kinds) > 1 or WorkstreamKind.RESEARCH in kinds:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def plan(self, request: str) -> MissionPlan:
        request = request.strip() or "default task"
        kinds = self._classify(request)
        gates: dict[str, list[str]] = {}
        gate_map = {
            WorkstreamKind.RESEARCH: ["at least 2 independent dated sources"],
            WorkstreamKind.CODE: ["tests pass", "reproducible command output"],
            WorkstreamKind.DOCUMENT: ["input and output files verified"],
            WorkstreamKind.CREATIVE_MEDIA: ["rendered media file exists", "file integrity verified"],
            WorkstreamKind.DATA: ["schema verified", "no silent truncation"],
            WorkstreamKind.AUTOMATION: ["dispatch and output health checks pass"],
            WorkstreamKind.DEVICE: ["permission and execution result verified"],
            WorkstreamKind.COMMERCE: ["user confirmation before external write"],
        }
        for kind in kinds:
            gates[kind.value] = gate_map[kind]
        risk = self._risk(request, kinds)
        return MissionPlan(
            mission_id=f"mission-{uuid.uuid4().hex[:8]}",
            user_request=request,
            workstreams=[kind.value for kind in kinds],
            risk_level=risk.value,
            selected_plugins=[f"{kind.value}-workflow" for kind in kinds],
            selected_models=["economy"] if risk == RiskLevel.LOW else ["specialist", "judge"],
            evidence_gates=gates,
        )

    def run(self, request: str) -> dict:
        plan = self.plan(request)
        return {
            "plan": asdict(plan),
            "pipeline": ["observe", "decompose", "retrieve", "select", "execute", "evidence", "verify", "learn"],
            "status": "planned",
        }


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    cmd = args[0] if args else "status"
    orch = Orchestrator()
    if cmd == "status":
        payload = orch.status()
    elif cmd in {"plan", "run"}:
        request = " ".join(args[1:]) if len(args) > 1 else "default task"
        payload = orch.plan(request) if cmd == "plan" else orch.run(request)
        if isinstance(payload, MissionPlan):
            payload = asdict(payload)
    else:
        print("Usage: python orchestrator.py {status|plan|run} [request]", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
