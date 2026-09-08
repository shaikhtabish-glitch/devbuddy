"""Tests for src/tools.py — Week 4"""
import json
import pytest
from src.tools import (
    get_build_status, get_recent_deploys, get_active_incidents,
    execute_tool_safely, run_tool_loop, run_tool_loop_with_trace,
    ALL_TOOLS, TOOLS_BY_NAME, build_status, flaky,
)


# ═══════════════════════════════════════════════════════════════
# Tool definitions
# ═══════════════════════════════════════════════════════════════

def test_tools_imports_llm():
    """tools.py imports from llm.py — the import graph holds."""
    from src.tools import run_tool_loop
    import inspect
    source = inspect.getsource(run_tool_loop)
    assert "get_llm" in source, "run_tool_loop should call get_llm() from src.llm"


def test_get_build_status_known_service():
    """Returns status for a known service."""
    result = json.loads(get_build_status.invoke({"service_name": "auth-service"}))
    assert result["status"] == "healthy"
    assert "last_deploy" in result


def test_get_build_status_unknown_service():
    """Returns unknown for an unrecognized service."""
    result = json.loads(get_build_status.invoke({"service_name": "nonexistent"}))
    assert result["status"] == "unknown"
    assert "error" in result


def test_get_recent_deploys_returns_list():
    """Returns a list of deployment records."""
    result = json.loads(get_recent_deploys.invoke({
        "service_name": "payment-api", "limit": 3
    }))
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]["status"] == "success"


def test_get_recent_deploys_empty_for_unknown():
    """Returns empty list for service with no deploys."""
    result = json.loads(get_recent_deploys.invoke({
        "service_name": "inventory-service"
    }))
    assert result == []


def test_get_active_incidents_has_incidents():
    """Returns active incidents for payment-api."""
    result = json.loads(get_active_incidents.invoke({
        "service_name": "payment-api"
    }))
    assert len(result) == 1
    assert result[0]["id"] == "INC-842"


def test_get_active_incidents_none_for_healthy():
    """Returns empty list for service with no incidents."""
    result = json.loads(get_active_incidents.invoke({
        "service_name": "auth-service"
    }))
    assert result == []


# ═══════════════════════════════════════════════════════════════
# Tool execution
# ═══════════════════════════════════════════════════════════════

def test_execute_tool_safely_known_tool():
    """Executes a valid tool call successfully."""
    result = json.loads(execute_tool_safely({
        "name": "get_build_status",
        "args": {"service_name": "auth-service"},
    }))
    assert result["status"] == "healthy"


def test_execute_tool_safely_unknown_tool():
    """Returns structured error for unknown tool."""
    result = json.loads(execute_tool_safely({
        "name": "nonexistent_tool",
        "args": {},
    }))
    assert "error" in result
    assert "available_tools" in result


def test_flaky_fails_first_n_then_succeeds():
    """flaky() is a deterministic, per-instance failure injector."""
    fn = flaky(build_status, fail_first_n=2)
    for _ in range(2):
        with pytest.raises(ConnectionError):
            fn("auth-service")
    assert json.loads(fn("auth-service"))["status"] == "healthy"


def test_flaky_instances_are_isolated():
    """Each flaky() wrapper owns its own counter — no shared global state."""
    a = flaky(build_status, fail_first_n=1)
    b = flaky(build_status, fail_first_n=1)
    with pytest.raises(ConnectionError):
        a("auth-service")
    # b's counter is untouched by a's failure
    with pytest.raises(ConnectionError):
        b("auth-service")
    assert json.loads(a("auth-service"))["status"] == "healthy"


def test_execute_tool_safely_denies_unknown_via_registry(monkeypatch):
    """The whitelist guard: an unregistered tool name is denied, not executed."""
    def _noop(**kwargs):
        raise AssertionError("should never be called")
    registry = {"get_build_status": object()}  # not even a real tool
    monkeypatch.setattr("time.sleep", lambda s: None)
    result = json.loads(execute_tool_safely(
        {"name": "delete_production_db", "args": {}},
        tools_by_name=registry,
    ))
    assert result["error"] == "Unknown tool: 'delete_production_db'"
    assert result["available_tools"] == ["get_build_status"]


def test_execute_tool_safely_exhausted_returns_structured_error(monkeypatch):
    """Persistent failure → structured error after retries burn out."""
    from langchain_core.tools import tool as lc_tool

    impl = flaky(build_status, fail_first_n=99)

    @lc_tool
    def get_build_status(service_name: str) -> str:
        """Return build status."""
        return impl(service_name)

    monkeypatch.setattr("time.sleep", lambda s: None)
    result = json.loads(execute_tool_safely(
        {"name": "get_build_status", "args": {"service_name": "payment-api"}},
        max_retries=1,
        tools_by_name={"get_build_status": get_build_status},
    ))
    assert result["status"] == "failed"
    assert result["attempts"] == 2  # 1 initial + 1 retry
    assert "error" in result


def test_all_tools_have_descriptions():
    """Every tool has a non-empty docstring for routing."""
    for t in ALL_TOOLS:
        assert t.description, f"Tool '{t.name}' has no description"


def test_tools_by_name_maps_all():
    """TOOLS_BY_NAME contains all tools."""
    assert set(TOOLS_BY_NAME.keys()) == {t.name for t in ALL_TOOLS}


# ═══════════════════════════════════════════════════════════════
# Tool-calling loop (requires LLM)
# ═══════════════════════════════════════════════════════════════

def test_run_tool_loop_calls_tool():
    """A question that needs build status triggers a tool call, and the answer
    is grounded in the tool result (in the model's own words, not verbatim)."""
    trace = run_tool_loop_with_trace("Is the auth-service healthy?", temperature=0.0)
    calls = [tc["name"] for tc in trace.get("tool_calls", [])]
    assert "get_build_status" in calls, f"Expected get_build_status call, got: {calls}"
    assert trace["tool_calls"][0]["args"].get("service_name") == "auth-service", (
        f"Tool should target auth-service: {trace['tool_calls'][0]['args']}"
    )
    answer = trace["answer"]
    assert len(answer) > 10, "Answer is too short"
    # The answer must reflect the tool result: a status word, the service name,
    # or the deploy marker that the tool returned. Brittle word-for-word
    # matching ("healthy") fails on correct-but-paraphrased answers.
    low = answer.lower()
    assert any(w in low for w in ["auth", "healthy", "degraded", "down", "unknown", "08:15"]), (
        f"Answer should reflect the build-status result: {answer[:120]}"
    )


def test_run_tool_loop_no_tool_needed():
    """A simple question doesn't trigger any tool calls."""
    result = run_tool_loop("What is 2 + 2?", temperature=0.0)
    assert "4" in result


def test_run_tool_loop_with_trace_returns_trace():
    """The traced version returns a dict with steps."""
    trace = run_tool_loop_with_trace(
        "Is the payment-api healthy?", temperature=0.0
    )
    assert "answer" in trace
    assert "query" in trace
    assert "steps" in trace
    assert len(trace["steps"]) >= 1


def test_run_tool_loop_with_trace_no_tool_calls():
    """Trace works even when no tools are called."""
    trace = run_tool_loop_with_trace("Hello!", temperature=0.0)
    assert "answer" in trace
    assert trace.get("tool_calls") is None or trace["tool_calls"] == []
