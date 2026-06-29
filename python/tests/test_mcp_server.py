"""Tests for src/mcp_server.py — Week 5"""
import json
import pytest


def test_mcp_server_imports():
    """mcp_server.py can be imported without errors."""
    from src import mcp_server
    assert mcp_server.mcp is not None
    assert mcp_server.mcp.name == "devbuddy-mcp"


def test_mcp_server_tools_registered():
    """All three tools are registered on the MCP server."""
    from src.mcp_server import mcp
    # FastMCP stores tools in _tool_manager
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "get_build_status" in tool_names
    assert "get_recent_deploys" in tool_names
    assert "get_active_incidents" in tool_names


def test_tools_are_callable_locally():
    """Each tool function can be called directly (without MCP)."""
    from src.mcp_server import get_build_status, get_recent_deploys, get_active_incidents

    r1 = json.loads(get_build_status("auth-service"))
    assert r1["status"] == "healthy"

    r2 = json.loads(get_recent_deploys("payment-api", limit=2))
    assert len(r2) == 2

    r3 = json.loads(get_active_incidents("payment-api"))
    assert len(r3) == 1
    assert r3[0]["id"] == "INC-842"


def test_tools_return_valid_json():
    """Every tool returns parseable JSON."""
    from src.mcp_server import get_build_status, get_recent_deploys, get_active_incidents

    for tool_fn in [get_build_status, get_recent_deploys, get_active_incidents]:
        result = tool_fn("auth-service")
        json.loads(result)  # should not raise
