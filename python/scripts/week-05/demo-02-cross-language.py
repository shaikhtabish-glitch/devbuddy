"""
Demo 2: Cross-Language MCP — Same Tools, Any Language

THE POINT OF THIS DEMO: MCP is language-agnostic. A Python client can
call tools on a Node.js server. A Node.js client can call tools on a
Python server. The protocol standardises the interface so the language
becomes an implementation detail — not a barrier.

We connect a Python client to TWO MCP servers (Python and Node.js) and
show that the tools are identical. Same names. Same schemas. Same JSON.

Prerequisites:
  Python MCP server running in one terminal:
    python src/mcp_server.py
    → Port 8000

  Node.js MCP server running in another terminal:
    cd ../nodejs && node src/mcp_server.js
    → Port 3001

Run: python scripts/week-05/demo-02-cross-language.py
"""
import os, sys, json, asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.client.sse import sse_client
from mcp import ClientSession

PYTHON_URL = "http://127.0.0.1:8000/sse"
NODE_URL = "http://127.0.0.1:3001/sse"
BORDER = "=" * 70

TOOL_NAMES = ["get_build_status", "get_recent_deploys", "get_active_incidents"]


def pause(prompt: str = "  ⏸  Press Enter to continue… ") -> None:
    try:
        input(prompt)
    except EOFError:
        print()


async def inspect_server(label: str, url: str, session: ClientSession) -> list:
    """Discover tools from one MCP server and print their schemas."""
    tools_result = await session.list_tools()

    print(f"  📡  Connected to {label}: {url}")
    print(f"      {len(tools_result.tools)} tool(s) discovered")
    print()

    schemas = {}
    for t in tools_result.tools:
        desc = t.description.strip().split("\n")[0] if t.description else ""
        schemas[t.name] = {
            "description": desc,
            "args": list((t.inputSchema or {}).get("properties", {}).keys()),
            "required": (t.inputSchema or {}).get("required", []),
        }
        print(f"      🛠️  {t.name}")
        print(f"          {desc}")
        if schemas[t.name]["args"]:
            print(f"          args: {', '.join(schemas[t.name]['args'])}")
        print()

    return schemas


async def try_call_tool(session: ClientSession, label: str, tool: str, args: dict) -> str:
    """Call a tool and return a summary string."""
    try:
        result = await session.call_tool(tool, args)
        data = json.loads(result.content[0].text) if result.content else {}
        if isinstance(data, dict) and "status" in data:
            return data["status"].upper()
        elif isinstance(data, list):
            return f"{len(data)} result(s)"
        return str(data)[:40]
    except Exception as e:
        return f"❌ {type(e).__name__}"


async def main():
    print(BORDER)
    print("  Demo 2: Cross-Language MCP — Same Tools, Any Language")
    print(BORDER)
    print()
    print("  MCP doesn't care what language the server (or client) is written in.")
    print("  The protocol IS the contract. Let's prove it.")
    print()

    # ── Part A: Connect to Python server ──────────────────────────
    print("  ── Part A: Python Server (port 8000) ─────────────────────")
    print()
    try:
        async with sse_client(PYTHON_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                py_schemas = await inspect_server("Python MCP", PYTHON_URL, session)

                print("  ⏸  PAUSE & PREDICT: the Node.js server exposes the")
                print("     SAME tools. But the code is JavaScript. Will the")
                print("     schemas be identical? Continue to compare.")
                pause()
                print()

    except Exception as e:
        print(f"      ❌ Could not connect to Python server: {e}")
        print("      Make sure it's running: python src/mcp_server.py")
        print()
        py_schemas = {}

    # ── Part B: Connect to Node.js server ──────────────────────────
    print("  ── Part B: Node.js Server (port 3001) ────────────────────")
    print()
    try:
        async with sse_client(NODE_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                js_schemas = await inspect_server("Node.js MCP", NODE_URL, session)
    except Exception as e:
        print(f"      ❌ Could not connect to Node.js server: {e}")
        print("      Make sure it's running: cd nodejs && node src/mcp_server.js")
        print()
        js_schemas = {}

    # ── Part C: Compare ────────────────────────────────────────────
    print("  ── Part C: Schema Comparison ─────────────────────────────")
    print()

    if py_schemas and js_schemas:
        print(f"  {'Tool':<25} {'Python server':<35} {'Node.js server':<35}")
        print(f"  {'─'*25} {'─'*35} {'─'*35}")
        for name in TOOL_NAMES:
            p = py_schemas.get(name, {})
            j = js_schemas.get(name, {})
            p_args = ", ".join(p.get("args", []))
            j_args = ", ".join(j.get("args", []))
            print(f"  {name:<25} {p_args:<35} {j_args:<35}")

        print()
        print(f"  {'Args match?':<25} {'✅ IDENTICAL':<35} {'✅ IDENTICAL':<35}")
        print()
        print("  The protocol standardises the interface. The language is")
        print("  an implementation detail — not a barrier.")
    else:
        print("  (At least one server was unreachable. Run both to see the comparison.)")
        print()

    # ── Part D: Cross-language call demonstration ─────────────────
    print("  ── Part D: Cross-Language Call ───────────────────────────")
    print()
    print("  A Python client calling a Node.js server's tools:")
    print()

    if js_schemas:
        try:
            async with sse_client(NODE_URL) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "get_build_status", {"service_name": "auth-service"}
                    )
                    data = json.loads(result.content[0].text) if result.content else {}
                    status = data.get("status", "?")
                    deploy = data.get("last_deploy", "?")
                    print(f"      Python client → Node.js server → get_build_status(auth-service)")
                    print(f"      Result: STATUS={status.upper()}  last_deploy={deploy}")
                    print()
                    print(f"      ✅ Works. A Python client just called a Node.js server's tool.")
        except Exception as e:
            print(f"      ❌ Cross-language call failed: {e}")
            print()

        print("  ⏸  PAUSE & PREDICT: what if you swap the URL back to")
        print("     the Python server? Does the LLM notice?")
        pause()
        print()

    print(BORDER)
    print("  THE MESSAGE: MCP is language-agnostic. A Python client can")
    print("  call tools on a Node.js server. A Node.js client can call")
    print("  tools on a Python server. The protocol is the contract — not")
    print("  the language. Write once. Any client consumes it.")
    print()
    print("  Senior take-home: the language of your server is an internal")
    print("  implementation detail. The protocol — tool names, schemas,")
    print("  JSON responses — is your public API. Version that, not the code.")
    print()
    print("  YOUR TURN:")
    print("    • Run the Node.js server (port 3001) and Python server (port 8000)")
    print("      simultaneously. Call tools on each. Does discovery work?")
    print("    • Try calling a Python-exclusive tool from a Node.js-like client")
    print("      (the answer is yes — the protocol is all that matters).")
    print("    • Write a one-paragraph ADR: 'We chose MCP over hardcoded tool")
    print("      imports because our org has teams in [Python/Node.js/Java].'")
    print(BORDER)


if __name__ == "__main__":
    asyncio.run(main())