"""
Week 5 — MCP Server: Shared Tool Ecosystem

Exposes tools from src/tools.py over the Model Context Protocol.
Write once. Any MCP client in any language can discover and call them.

Imports: from src.tools import ...
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="devbuddy-mcp",
    instructions=(
        "DevBuddy MCP Server — exposes build status, deployment history, "
        "and active incident data for engineering services."
    ),
)


# ── Tools — wrapped as MCP-native functions ───────────────────
#
# We can't directly pass LangChain @tool objects to FastMCP (they're
# StructuredTool instances, not plain functions). Instead, we re-wrap
# the logic as MCP tools using FastMCP's @tool decorator.

@mcp.tool()
def get_build_status(service_name: str) -> str:
    """
    Return the current build/health status for a given service.
    Returns a JSON string with status and last deploy timestamp.
    Status is one of: healthy, degraded, down, unknown.
    """
    statuses = {
        "auth-service": {"status": "healthy", "last_deploy": "2026-06-28T08:15:00Z"},
        "payment-api": {"status": "degraded", "last_deploy": "2026-06-28T06:45:00Z", "failing_since": "2026-06-28T07:30:00Z"},
        "inventory-service": {"status": "unknown", "last_deploy": "2026-06-20T11:00:00Z"},
    }
    data = statuses.get(service_name)
    if data is None:
        return json.dumps({"status": "unknown", "error": f"No data for service '{service_name}'"})
    return json.dumps(data)


@mcp.tool()
def get_recent_deploys(service_name: str, limit: int = 5) -> str:
    """
    Return the last N deployments for a given service.
    Each deploy has: sha, author, timestamp, status.
    Status is one of: success, failed, rolling_back.
    """
    deploys = {
        "auth-service": [
            {"sha": "abc123def456", "author": "tabish", "timestamp": "2026-06-28T08:15:00Z", "status": "success"},
            {"sha": "789ghi012jkl", "author": "alex", "timestamp": "2026-06-27T14:30:00Z", "status": "success"},
        ],
        "payment-api": [
            {"sha": "def789ghi012", "author": "maria", "timestamp": "2026-06-28T06:45:00Z", "status": "success"},
            {"sha": "jkl345mno678", "author": "maria", "timestamp": "2026-06-27T22:00:00Z", "status": "rolling_back"},
            {"sha": "pqr901stu234", "author": "jordan", "timestamp": "2026-06-27T20:15:00Z", "status": "failed"},
        ],
        "inventory-service": [],
    }
    return json.dumps(deploys.get(service_name, [])[:limit], indent=2)


@mcp.tool()
def get_active_incidents(service_name: str) -> str:
    """
    Return any active (unresolved) incidents for a given service.
    Returns a JSON list of incident objects with id, severity, and summary.
    """
    incidents = {
        "payment-api": [
            {"id": "INC-842", "severity": "Sev1", "summary": "payment-api latency spike. 15% of requests affected. Error code 408.", "status": "investigating"},
        ],
        "auth-service": [],
        "inventory-service": [
            {"id": "INC-901", "severity": "Sev3", "summary": "inventory-service data inconsistency between primary and replica.", "status": "investigating", "tracking": ["PROJ-891", "PROJ-892"]},
        ],
    }
    return json.dumps(incidents.get(service_name, []), indent=2)


# ── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run_stdio_async())
