#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict

from engine import MissionEngine


def build_request(text: str, workstreams: list[str] | None = None, risk: str = "low") -> dict:
    return {
        "mission_id": f"mission-{uuid.uuid4().hex[:8]}",
        "user_request": text or "default task",
        "workstreams": workstreams or ["code"],
        "risk_level": risk,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evidence-gated Minis mission orchestrator")
    sub = parser.add_subparsers(dest="command", required=False)
    sub.add_parser("status", help="show discovered skills and connectors")
    for name in ("plan", "run", "preview"):
        cmd = sub.add_parser(name)
        cmd.add_argument("request", nargs="*", help="mission request")
        cmd.add_argument("--workstream", action="append", dest="workstreams")
        cmd.add_argument("--risk", choices=("low", "medium", "high", "critical"), default="low")
        cmd.add_argument("--confirm", action="store_true", help="approve external side effects")
    trace = sub.add_parser("trace", help="show a mission trace")
    trace.add_argument("mission_id")
    args = parser.parse_args(argv)
    engine = MissionEngine()

    if args.command in (None, "status"):
        print(json.dumps(engine.registry.summary(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "trace":
        path = engine.workspace / f"{args.mission_id}.jsonl"
        if not path.exists():
            print(json.dumps({"error": "trace_not_found", "mission_id": args.mission_id}, ensure_ascii=False))
            return 1
        print(path.read_text(encoding="utf-8"), end="")
        return 0

    request = " ".join(args.request).strip() or "default task"
    mission = build_request(request, args.workstreams, args.risk)
    if args.command == "plan":
        print(json.dumps(mission, ensure_ascii=False, indent=2))
        return 0
    result = engine.preview(mission) if args.command == "preview" else engine.execute(mission, confirmed=args.confirm)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2, default=str))
    return 0 if result.status in {"previewed", "passed", "awaiting_approval"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
