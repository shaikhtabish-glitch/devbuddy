"""
Demo 1: MCP Client — Connect, Discover, Call

Connects to the DevBuddy MCP server, lists available tools, and calls
them with real data from the Week 3 RAG index. Demonstrates the full
client → server → tool → response path.

Run: python scripts/week-05/demo-01-mcp-client.py
(Requires Qdrant running: docker-compose up -d)
"""
import asyncio, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "src", "mcp_server.py")

TOOL_ICONS = {
    "get_build_status": "🏗️",
    "get_recent_deploys": "🚀",
    "get_active_incidents": "🚨",
}


async def main():
    server_params = StdioServerParameters(command="python", args=[SERVER_SCRIPT])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()

            print()
            print("=" * 62)
            print("  MCP Client  —  Connect, Discover, Call")
            print("=" * 62)
            print()

            # ── DISCOVER ───────────────────────────────────────
            print("  📡  DISCOVER: list_tools()")
            print()
            for t in tools_result.tools:
                desc = t.description.strip().split("\n")[0] if t.description else "(no description)"
                icon = TOOL_ICONS.get(t.name, "🔧")
                print(f"      {icon}  {t.name}")
                print(f"          {desc}")
            print()

            # ── BUILD STATUS ───────────────────────────────────
            print("  " + "─" * 59)
            print("  🏗️  QUERY: get_build_status")
            print("  " + "─" * 59)
            print()
            for service in ["auth-service", "payment-api"]:
                result = await session.call_tool(
                    "get_build_status", {"service_name": service}
                )
                data = result.content[0].text if result.content else "{}"
                parsed = json.loads(data)
                print(f"      →  RESPONSE  {service}: {parsed.get('status', '?').upper()}")
                print(f"                  last deploy  {parsed.get('last_deploy', '?')}")
                print()

            # ── DEPLOYS ────────────────────────────────────────
            print("  " + "─" * 59)
            print("  🚀  QUERY: get_recent_deploys(payment-api, limit=2)")
            print("  " + "─" * 59)
            print()
            result = await session.call_tool(
                "get_recent_deploys", {"service_name": "payment-api", "limit": 2}
            )
            deploys = json.loads(result.content[0].text) if result.content else []
            for d in deploys:
                status_icon = "✅" if d.get("status") == "success" else "❌"
                print(f"      →  {status_icon}  {d.get('sha','?')[:12]}  "
                      f"{d.get('author','?'):<8}  {d.get('timestamp','?')}")
            print()

            # ── INCIDENTS ──────────────────────────────────────
            print("  " + "─" * 59)
            print("  🚨  QUERY: get_active_incidents(payment-api)")
            print("  " + "─" * 59)
            print()
            result = await session.call_tool(
                "get_active_incidents", {"service_name": "payment-api"}
            )
            incidents = json.loads(result.content[0].text) if result.content else []
            if incidents:
                for inc in incidents:
                    sev = inc.get("severity", "?")
                    print(f"      →  {sev:<6}  {inc.get('id','?')}")
                    print(f"                  {inc.get('summary','?')}")
            else:
                print("      →  (no active incidents)")
            print()

            print("=" * 62)
            print("  All data from the Week 3 RAG index (Qdrant).")
            print("  Same tools as Week 4. Any MCP client can call them.")
            print("=" * 62)
            print()


if __name__ == "__main__":
    asyncio.run(main())
