"""Tests for src/tools.py — Week 4"""
import json
import pytest
from src.tools import (
    get_build_status, get_recent_deploys, get_active_incidents,
    execute_tool_safely, run_tool_loop, run_tool_loop_with_trace,
    ALL_TOOLS, TOOLS_BY_NAME,
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
    """A question that needs build status triggers a tool call."""
    result = run_tool_loop("Is the auth-service healthy?", temperature=0.0)
    assert len(result) > 10, "Answer is too short"
    assert any(w in result.lower() for w in ["healthy", "auth"]), (
        f"Answer should reference auth-service health: {result[:100]}"
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
