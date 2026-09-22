"""
Demo 4: Security & Scope — What Does Your MCP Server Expose?

THE POINT OF THIS DEMO: your MCP server is now reachable over the network.
Anyone who can connect can discover your tools. Before you expose a tool,
ask: what's the blast radius? Is it read-only? Who can call it?

This demo connects to the MCP server, inspects each tool's schema, and
walks through the security posture of each one — what it exposes, what
it could be abused for, and what guards you'd add before production.

Prerequisites:
  Qdrant vector DB running:
    docker-compose up -d   (from repo root)

  MCP server running on port 8000:
    python src/mcp_server.py

Run: python scripts/week-05/demo-04-security-scope.py
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


async def inspect_tool(session: ClientSession, name: str, args: dict) -> dict:
    """Call a tool and return the parsed JSON result."""
    try:
        result = await session.call_tool(name, args)
        if result.content:
            return json.loads(result.content[0].text)
        return {"status": "unknown", "reason": "empty response"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}


async def main():
    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print(BORDER)
            print("  Demo 4: Security & Scope — What Does Your MCP Server Expose?")
            print(BORDER)
            print()

            # ── Step 1: Discover all tools ─────────────────────────
            tools_result = await session.list_tools()
            print(f"  Number of tools exposed: {len(tools_result.tools)}")
            print()
            print("  Every tool is a potential attack surface. Let's review each one.")
            print()

            for t in tools_result.tools:
                desc = t.description.strip().split("\n")[0] if t.description else ""
                params = list((t.inputSchema or {}).get("properties", {}).keys())
                req = (t.inputSchema or {}).get("required", [])

                print(f"  ── Tool: {t.name} ──────────────────────────────────")
                print(f"      {desc}")
                print(f"      Parameters: {', '.join(params) if params else '(none)'}")
                print(f"      Required:   {', '.join(req) if req else '(none)'}")
                print()

                print(f"      Security assessment:")
                print(f"      • Read-only?     ✅ YES — examines documents, never writes")
                print(f"      • Auth required? ❌ NO  — anyone with network access can call")
                print(f"      • Rate-limited?  ❌ NO  — unlimited calls per connection")
                print(f"      • Blast radius:  HOST data shared/data/ files via RAG + LLM")
                print()

                print("  ⏸  PAUSE & PREDICT: what's the worst thing someone could")
                print("     do with this tool if they reached your server?")
                pause()
                print()

                # Demonstrate the tool
                if t.name == "get_build_status":
                    result = await inspect_tool(session, t.name, {"service_name": "auth-service"})
                    print(f"      Sample call → {result.get('status', '?')}")
                elif t.name == "get_recent_deploys":
                    result = await inspect_tool(session, t.name, {"service_name": "payment-api", "limit": 1})
                    count = len(result) if isinstance(result, list) else 0
                    print(f"      Sample call → {count} deployment(s)")
                elif t.name == "get_active_incidents":
                    result = await inspect_tool(session, t.name, {"service_name": "payment-api"})
                    count = len(result) if isinstance(result, list) else 0
                    print(f"      Sample call → {count} incident(s)")
                print()

            # ── Step 2: The attack surface ─────────────────────────
            print("  ── The Attack Surface ───────────────────────────────")
            print()
            print("  These tools are read-only and RAG-powered, so the blast radius")
            print("  is limited to the documents in shared/data/. But consider:")
            print()
            print("  • Enumeration: an attacker can call get_build_status with any")
            print("    service name and learn your infrastructure topology.")
            print("  • Data leakage: incident IDs, deploy SHAs, and timestamps")
            print("    are metadata about your engineering process.")
            print("  • Prompt injection: service_name is fed to the LLM. A crafted")
            print("    value could hijack the extraction prompt.")
            print()

            print("  ⏸  PAUSE & PREDICT: what if get_build_status accepted a")
            print("     'deploy' boolean that, when true, triggered a rollback?")
            print("     What would your security posture need to be?")
            pause()
            print()

            # ── Step 3: Hardening checklist ─────────────────────────
            print("  ── Hardening Checklist ──────────────────────────────")
            print()
            print("  Before exposing your MCP server beyond localhost:")
            print()
            print("  ✅  Read-only by default")
            print("      Start with tools that only read data. Add write tools")
            print("      only after auth and audit are in place.")
            print()
            print("  ✅  Input validation")
            print("      Never pass user-supplied strings directly to the LLM or")
            print("      to system commands. Validate, sanitize, and constrain.")
            print()
            print("  ✅  Authentication")
            print("      API key, OAuth, or mTLS. The MCP server should know WHO")
            print("      is calling before it answers.")
            print()
            print("  ✅  Rate limiting")
            print("      A runaway agent can call your tool 10,000 times in a loop.")
            print("      Cap calls per client per minute.")
            print()
            print("  ✅  Audit logging")
            print("      Every tool call: who, what args, when, what result.")
            print("      If you can't trace a call, you can't investigate an incident.")
            print()

            print(BORDER)
            print("  THE MESSAGE: Every tool is a potential attack surface.")
            print("  Your MCP server's security posture is determined by your")
            print("  CODE — not by the model's prompt.")
            print()
            print("  Senior take-home: same principle as Week 4, one layer out.")
            print("  The model proposes a tool call. Your app layer validates it.")
            print("  The model proposes a connection. Your server auth validates it.")
            print()
            print("  YOUR TURN:")
            print("    • Add a write tool to mcp_server.py (e.g., set_deploy_status).")
            print("      What security implications does it have?")
            print("    • Write a 1-paragraph security note: 'Before exposing this")
            print("      to the wider org, I would add [X] because [Y].'")
            print("    • Add rate limiting to mcp_server.py. What happens when")
            print("      a client exceeds the limit? Does the error inform them?")
            print(BORDER)


if __name__ == "__main__":
    asyncio.run(main())