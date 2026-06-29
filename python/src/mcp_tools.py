"""
MCP Tools — sync wrappers for calling tools via the MCP server.

Each function starts an MCP session, calls the tool, and returns the result.
Used by the agent instead of direct imports from src/tools.

The agent uses five tools:
  4 via MCP server:  get_build_status, get_recent_deploys,
                      get_active_incidents, get_service_docs
  1 direct (non-MCP): get_current_time — shows local-only tools
"""
import os, sys, json, asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from datetime import datetime

SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "mcp_server.py")


def _call_mcp_tool(tool_name: str, args: dict) -> str:
    """Call a tool on the MCP server and return the result text."""
    async def _call():
        server_params = StdioServerParameters(command="python", args=[SERVER_SCRIPT])
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, args)
                return result.content[0].text if result.content else "no result"

    return asyncio.run(_call())


# ═══════════════════════════════════════════════════════════════
# Tools via MCP Server
# ═══════════════════════════════════════════════════════════════

def get_build_status(service_name: str) -> str:
    """Return the current build/health status for a given service. (via MCP)"""
    return _call_mcp_tool("get_build_status", {"service_name": service_name})


def get_recent_deploys(service_name: str, limit: int = 5) -> str:
    """Return the last N deployments for a given service. (via MCP)"""
    return _call_mcp_tool("get_recent_deploys", {
        "service_name": service_name, "limit": limit
    })


def get_active_incidents(service_name: str) -> str:
    """Return any active incidents for a given service. (via MCP)"""
    return _call_mcp_tool("get_active_incidents", {"service_name": service_name})


def get_service_docs(service_name: str) -> str:
    """Return relevant documentation for a given service from Qdrant. (via MCP)"""
    return _call_mcp_tool("get_service_docs", {"service_name": service_name})


# ═══════════════════════════════════════════════════════════════
# Direct Tool (non-MCP) — shows the boundary
# ═══════════════════════════════════════════════════════════════

def get_current_time() -> str:
    """
    Return the current server time.
    NOT exposed on the MCP server — only available locally.
    Shows that not every tool needs to be shared across the org.
    """
    return json.dumps({
        "time": datetime.now().isoformat(),
        "timezone": str(datetime.now().astimezone().tzinfo),
        "note": "Local-only tool — not available to other MCP clients",
    })
