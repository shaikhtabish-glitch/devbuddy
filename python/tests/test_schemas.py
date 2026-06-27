"""Tests for src/schemas.py — Week 2"""
import pytest
from src.schemas import BuildCheck, analyze_pr


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
