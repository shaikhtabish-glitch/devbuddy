"""
Demo 1: Wire an MCP Server — Client Discovers, Server Serves

THE POINT OF THIS DEMO is not that we called a tool — it's that the
client discovered the tool. In Week 4, tools were hardcoded imports.
Here, the client asked "what tools exist?" and got an answer dynamically.
No import. No shared code. A protocol.

The server exposes tools as a protocol, not a function call.
The client doesn't import anything — it discovers.

Prerequisites:
  Qdrant vector DB running:
    docker-compose up -d   (from repo root)
    curl http://localhost:6333/healthz

  MCP server running in another terminal:
    python src/mcp_server.py
    → Server running on http://localhost:8000/sse

Run: python scripts/week-05/demo-01-wire-server.py
"""
import os, sys, json, asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.client.sse import sse_client
from mcp import ClientSession

MCP_URL = "http://127.0.0.1:8000/sse"
BORDER = "=" * 70


def pause(prompt: str = "  ⏸  Press Enter to continue… ") -> None:
    try:
        input(prompt)
    except EOFError:
        print()


async def main():
    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print(BORDER)
            print("  Demo 1: Wire an MCP Server — Discover, Call, Repeat")
            print(BORDER)
            print()

            # ── Step 1: Discover ──────────────────────────────────
            print("  ── Step 1: Discover — list_tools() ────────────────")
            print()
            print("  The client doesn't know what tools exist. It asks the")
            print("  server. In Week 4, tools were hardcoded imports.")
            print("  Here, they are DISCOVERED at runtime.")
            print()

            tools_result = await session.list_tools()

            print(f"  Server says: {len(tools_result.tools)} tool(s) available")
            print()
            for i, t in enumerate(tools_result.tools, 1):
                desc = t.description.strip().split("\n")[0] if t.description else "(no description)"
                print(f"    [{i}] {t.name}")
                print(f"        {desc}")
                if t.inputSchema:
                    params = t.inputSchema.get("properties", {})
                    req = t.inputSchema.get("required", [])
                    if params:
                        print(f"        args: {', '.join(params.keys())}")
                    if req:
                        print(f"        required: {', '.join(req)}")
            print()

            print("  ⏸  PAUSE & PREDICT: the server is Python. Can a Node.js")
            print("     client call these same tools? Continue to find out.")
            pause()
            print()

            # ── Step 2: Call a tool ────────────────────────────────
            print("  ── Step 2: Call — get_build_status ────────────────")
            print()
            print("  Same tool as Week 4. Same arguments. Same return shape.")
            print("  But it's now on a SHARED SERVER, not a private import.")
            print()

            for service in ["auth-service", "payment-api", "inventory-service"]:
                try:
                    result = await session.call_tool(
                        "get_build_status", {"service_name": service}
                    )
                    data = json.loads(result.content[0].text) if result.content else {}
                    status = data.get("status", "?")
                    deploy = data.get("last_deploy", "?")
                    print(f"      {service:<20}  status: {status.upper():<10}  last deploy: {deploy}")
                except Exception as e:
                    print(f"      {service:<20}  ❌ {e}")

            print()

            # ── Step 3: Call another tool ──────────────────────────
            print("  ── Step 3: Call — get_recent_deploys ───────────────")
            print()
            result = await session.call_tool(
                "get_recent_deploys", {"service_name": "payment-api", "limit": 3}
            )
            raw = json.loads(result.content[0].text) if result.content else []
            deploys = raw if isinstance(raw, list) else []
            if deploys:
                for d in deploys:
                    icon = "✅" if d.get("status") == "success" else "❌"
                    print(f"      {icon}  {d.get('sha','?')[:12]}  {d.get('author','?'):<10}  {d.get('timestamp','?')}")
            else:
                print("      (no deployment data available)")
            print()

            # ── Step 4: Call a third ───────────────────────────────
            print("  ── Step 4: Call — get_active_incidents ─────────────")
            print()
            result = await session.call_tool(
                "get_active_incidents", {"service_name": "payment-api"}
            )
            raw = json.loads(result.content[0].text) if result.content else []
            incidents = raw if isinstance(raw, list) else []
            if incidents:
                for inc in incidents:
                    print(f"      {inc.get('severity','?'):<6}  {inc.get('id','?'):<10}  {inc.get('summary','?')[:60]}")
            else:
                print("      (no active incidents)")
            print()

            # ── Step 5: Recap ──────────────────────────────────────
            print(BORDER)
            print("  THE SHIFT: Week 4 imported tools. Week 5 discovers them.")
            print()
            print("  Week 4:  from src.tools import get_build_status")
            print("  Week 5:  session.list_tools()  # → 'get_build_status' found!")
            print()
            print("  The tool interface is IDENTICAL. The tool LOCATION changed.")
            print("  Same contracts. Same JSON. Now shared across everything.")
            print("  Write once. Any MCP client consumes it.")
            print()
            print("  YOUR TURN:")
            print("    • Add a new tool to mcp_server.py, restart the server,")
            print("      and re-run this demo. Does list_tools() show it?")
            print("    • Change the MCP_URL to http://localhost:3001/sse")
            print("      (Node.js server). Does discovery still work?")
            print("    • Break the server (stop it). What error do you get?")
            print(BORDER)


if __name__ == "__main__":
    asyncio.run(main())