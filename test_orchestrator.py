import json
import subprocess
import sys
from pathlib import Path

from orchestrator import Orchestrator, RiskLevel


ROOT = Path(__file__).parent


def test_code_request_is_classified_and_serializable():
    plan = Orchestrator().plan("fix the code bug")
    assert "code" in plan.workstreams
    assert plan.risk_level == RiskLevel.LOW.value
    assert json.loads(json.dumps(plan.__dict__))


def test_research_request_gets_research_gate():
    plan = Orchestrator().plan("research current AI news")
    assert plan.workstreams == ["research"]
    assert "at least 2 independent dated sources" in plan.evidence_gates["research"]
    assert plan.risk_level == RiskLevel.MEDIUM.value


def test_payment_request_is_critical():
    plan = Orchestrator().plan("결제 처리 자동화")
    assert plan.risk_level == RiskLevel.CRITICAL.value
    assert "commerce" in plan.workstreams
    assert "user confirmation before external write" in plan.evidence_gates["commerce"]


def test_run_returns_complete_pipeline():
    result = Orchestrator().run("write a report")
    assert result["status"] == "planned"
    assert result["pipeline"][-1] == "learn"
    assert result["plan"]["workstreams"] == ["document"]


def test_cli_plan_command():
    completed = subprocess.run(
        [sys.executable, "orchestrator.py", "plan", "analyze data"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["workstreams"] == ["data"]
    assert payload["evidence_gates"]["data"]
