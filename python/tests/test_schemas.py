"""Tests for src/schemas.py — Week 2"""
import json
import pytest
from pydantic import ValidationError
from src.schemas import (
    BuildCheck, analyze_pr,
    ServiceReadinessReport, ServiceInfo, BuildStatus,
    DeployRecord, DeploymentInfo, EvidenceChunk, ReadinessVerdict,
)


# ═══════════════════════════════════════════════════════════════
# BuildCheck — in-session schema (requires OpenRouter)
# ═══════════════════════════════════════════════════════════════

def test_buildcheck_model():
    """BuildCheck can be created with valid fields."""
    bc = BuildCheck(
        project="auth-service",
        severity="high",
        summary="Fixed login redirect loop",
        affected_files=["src/auth.py", "tests/test_auth.py"],
    )
    assert bc.project == "auth-service"
    assert bc.severity == "high"


def test_analyze_pr_returns_typed_object():
    """analyze_pr returns a BuildCheck, not a string."""
    diff = "Fix login bug\n\nChanged auth.py line 42"
    result = analyze_pr(title="Fix login bug", diff=diff, temperature=0.0)
    assert isinstance(result, BuildCheck), f"Expected BuildCheck, got {type(result).__name__}"
    assert result.project, "project field is empty"
    assert result.severity in ("low", "medium", "high", "critical"), f"Invalid severity: {result.severity}"
    assert result.summary, "summary field is empty"
    assert len(result.affected_files) > 0, "affected_files is empty"


def test_analyze_pr_temperature_zero_is_deterministic():
    """Same input at temperature=0 produces identical output."""
    diff = "Fix login bug\n\nChanged auth.py line 42"
    r1 = analyze_pr(title="Fix login bug", diff=diff, temperature=0.0)
    r2 = analyze_pr(title="Fix login bug", diff=diff, temperature=0.0)
    assert r1.severity == r2.severity, "Temperature=0 should be deterministic"


def test_analyze_pr_with_sample_data():
    """analyze_pr works with the provided sample diff."""
    with open("../shared/data/sample-diff.txt") as f:
        diff = f.read()
    result = analyze_pr(title="Fix login redirect loop in auth-service", diff=diff, temperature=0.0)
    assert isinstance(result, BuildCheck)


def test_schemas_imports_llm():
    """schemas.py imports from llm.py — the import graph holds."""
    from src.schemas import analyze_pr
    import inspect
    source = inspect.getsource(analyze_pr)
    assert "get_llm" in source, "analyze_pr should call get_llm() from src.llm"


# ═══════════════════════════════════════════════════════════════
# ServiceReadinessReport — self-learning schema (pure Pydantic)
#
# These tests validate the schema with mock data.
# No API calls. No network. Instant feedback.
# Engineers can add more scenarios by extending the JSON files.
# ═══════════════════════════════════════════════════════════════

# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def healthy_data():
    with open("../shared/data/service-readiness-healthy.json") as f:
        return json.load(f)


@pytest.fixture
def degraded_data():
    with open("../shared/data/service-readiness-degraded.json") as f:
        return json.load(f)


@pytest.fixture
def unknown_data():
    with open("../shared/data/service-readiness-unknown.json") as f:
        return json.load(f)


# ── Happy path: all three scenarios validate ──────────────────

def test_service_readiness_healthy_validates(healthy_data):
    """Healthy auth-service report passes validation."""
    report = ServiceReadinessReport.model_validate(healthy_data)
    assert report.service.name == "auth-service"
    assert report.build.status == "healthy"
    assert report.verdict.ready is True
    assert report.verdict.confidence == "high"
    assert report.verdict.blockers == []
    assert len(report.evidence) == 2


def test_service_readiness_degraded_validates(degraded_data):
    """Degraded payment-api report passes validation."""
    report = ServiceReadinessReport.model_validate(degraded_data)
    assert report.service.name == "payment-api"
    assert report.build.status == "degraded"
    assert report.build.failing_since is not None
    assert report.verdict.ready is False
    assert len(report.verdict.blockers) == 3
    assert len(report.deployment.recent_deploys) == 3


def test_service_readiness_unknown_validates(unknown_data):
    """Unknown inventory-service report passes validation."""
    report = ServiceReadinessReport.model_validate(unknown_data)
    assert report.service.name == "inventory-service"
    assert report.build.status == "unknown"
    assert report.build.failing_since is None
    assert report.verdict.ready is False
    assert report.verdict.confidence == "low"
    assert report.evidence == []


# ── Validation: cross-field invariants ────────────────────────

def test_readiness_contradiction_ready_with_blockers():
    """ready=True + non-empty blockers → model_validator rejects."""
    data = {
        "service": {"name": "test-svc", "version": "1.0.0", "owner_team": "qa"},
        "build": {"status": "healthy", "last_deploy": "2026-06-28T00:00:00Z", "failing_since": None},
        "deployment": {"recent_deploys": [], "active_incidents": []},
        "verdict": {
            "ready": True,
            "confidence": "high",
            "blockers": ["build is red"],
            "recommended_next_steps": []
        },
        "evidence": [
            {"source": "tool", "content": "build=green", "relevance_score": None},
        ],
    }
    with pytest.raises(ValidationError, match="Contradiction"):
        ServiceReadinessReport.model_validate(data)


def test_readiness_not_ready_no_evidence_high_confidence():
    """ready=False with no evidence and confidence='high' → rejected."""
    data = {
        "service": {"name": "test-svc", "version": "1.0.0", "owner_team": "qa"},
        "build": {"status": "healthy", "last_deploy": "2026-06-28T00:00:00Z", "failing_since": None},
        "deployment": {"recent_deploys": [], "active_incidents": []},
        "verdict": {
            "ready": False,
            "confidence": "high",
            "blockers": [],
            "recommended_next_steps": []
        },
        "evidence": [],
    }
    with pytest.raises(ValidationError):
        ServiceReadinessReport.model_validate(data)


def test_failing_since_required_when_degraded():
    """status='degraded' + failing_since=None → field_validator rejects."""
    data = {
        "service": {"name": "test-svc", "version": "1.0.0", "owner_team": "qa"},
        "build": {"status": "degraded", "last_deploy": "2026-06-28T00:00:00Z", "failing_since": None},
        "deployment": {"recent_deploys": [], "active_incidents": []},
        "verdict": {
            "ready": False,
            "confidence": "low",
            "blockers": ["build degraded"],
            "recommended_next_steps": []
        },
        "evidence": [],
    }
    with pytest.raises(ValidationError, match="failing_since"):
        ServiceReadinessReport.model_validate(data)


def test_nested_deploy_record_validation():
    """DeployRecord with invalid status → rejected."""
    with pytest.raises(ValidationError):
        DeployRecord(
            sha="abc123",
            author="test",
            timestamp="2026-06-28T00:00:00Z",
            status="in_progress"  # not in Literal
        )


def test_valid_report_round_trips_through_json(healthy_data):
    """Validate → dump → re-validate. Schema survives serialization."""
    report = ServiceReadinessReport.model_validate(healthy_data)
    dumped = report.model_dump_json(indent=2)
    reloaded = ServiceReadinessReport.model_validate_json(dumped)
    assert reloaded.service.name == report.service.name
    assert reloaded.verdict.ready == report.verdict.ready
