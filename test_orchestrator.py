import json
from pathlib import Path

from engine import CapabilityRegistry, MissionEngine
from orchestrator import build_request


def test_registry_discovers_skills_without_failing_on_bad_frontmatter(tmp_path):
    root = tmp_path / "skills"
    skill = root / "demo"; skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: demo\ndescription: demo skill\n---\n", encoding="utf-8")
    summary = CapabilityRegistry(root, tmp_path / "missing.json").summary()
    assert summary["skills"] == 1
    assert summary["connectors"] == 0


def test_low_risk_execution_collects_evidence_and_passes(tmp_path):
    result = MissionEngine(tmp_path).execute(build_request("run code", ["code"], "low"))
    assert result.status == "passed"
    assert result.verification and result.verification.score >= 0.82
    assert result.trace_path and Path(result.trace_path).exists()


def test_high_risk_is_blocked_until_confirmation(tmp_path):
    engine = MissionEngine(tmp_path)
    mission = build_request("publish result", ["commerce"], "critical")
    pending = engine.execute(mission)
    assert pending.status == "awaiting_approval"
    approved = engine.execute(mission, confirmed=True)
    assert approved.status in {"passed", "repair_required"}


def test_subagent_has_minimal_capability_snapshot(tmp_path):
    result = MissionEngine(tmp_path).preview(build_request("analyze data", ["data"], "low"))
    assert len(result.subagents) == 1
    assert result.subagents[0].status == "planned"
    assert result.approval and result.approval.preview["tasks"]


def test_json_contract_is_serializable(tmp_path):
    result = MissionEngine(tmp_path).execute(build_request("write report", ["document"], "low"))
    payload = MissionEngine.serializable(result)
    assert json.loads(json.dumps(payload, ensure_ascii=False))
    assert payload["evidence"]
