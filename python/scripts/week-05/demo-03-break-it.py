"""
Demo 3: Break It — MCP Failure Patterns You Will Ship

THE POINT OF THIS DEMO: MCP connections fail in predictable ways.
Wrong port, wrong transport, wrong tool name, server down. These are not
bugs — they are the most common production issues. Learn the error messages
now so you recognise them on-call.

  Act 1 — Wrong port: server exists, but on a different port
  Act 2 — Wrong tool name: valid connection, tool doesn't exist
  Act 3 — Server down: nobody listening on the endpoint
  Act 4 — Recovery: fix the issue, call succeeds

Prerequisites:
  Qdrant vector DB running:
    docker-compose up -d   (from repo root)

  MCP server running on port 8000:
    python src/mcp_server.py

Run: python scripts/week-05/demo-03-break-it.py
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


def print_error(label: str, error: Exception) -> None:
    """Print a formatted error with the key message highlighted."""
    msg = str(error)
    key = type(error).__name__
    print(f"      ❌  [{key}] {msg[:120]}")
    print()


async def connect_and_call(url: str, tool: str, args: dict) -> str | None:
    """Try to connect and call a tool. Return result text or None on failure."""
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, args)
                return result.content[0].text if result.content else None
    except Exception as e:
        raise


async def main():
    print(BORDER)
    print("  Demo 3: Break It — MCP Failure Patterns")
    print(BORDER)
    print()
    print("  The most important skill: recognising error messages.")
    print("  These are the patterns you will debug on-call.")
    print()

    # ── Act 1: Wrong port ────────────────────────────────────────
    print("  ── Act 1: Wrong Port ─────────────────────────────────────")
    print()
    print("  Server is on port 8000. You connect to port 9999.")
    print()
    print("  ⏸  PAUSE & PREDICT: what error do you expect?")
    pause()

    wrong_port = "http://127.0.0.1:9999/sse"
    try:
        await connect_and_call(wrong_port, "get_build_status", {"service_name": "auth-service"})
        print("      ❓  Unexpected success — is something running on port 9999?")
    except Exception as e:
        print_error("Wrong port", e)

    print()
    print("  KEY INSIGHT: Connection refused is a NETWORK error, not a protocol error.")
    print("  The client never reached the server. Check port, firewall, and URL.")
    print()

    # ── Act 2: Wrong tool name ───────────────────────────────────
    print("  ── Act 2: Wrong Tool Name ────────────────────────────────")
    print()
    print("  Server is running. You connect successfully. But you ask for")
    print("  a tool that doesn't exist.")
    print()
    print("  ⏸  PAUSE & PREDICT: does the client crash, or does it get")
    print("     a structured error?")
    pause()
    print()

    try:
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("get_buildstatus", {"service_name": "auth-service"})
                print(f"      Result: {result.content[0].text if result.content else 'empty'}")
    except Exception as e:
        print_error("Wrong tool name", e)

    print()
    print("  KEY INSIGHT: Unknown tool errors come from the SERVER, not the client.")
    print("  The protocol works — the tool just doesn't exist in the registry.")
    print("  Check: misspellings, case, server version (does it have the latest tools?).")
    print()

    # ── Act 3: Server down ───────────────────────────────────────
    print("  ── Act 3: Server Down ────────────────────────────────────")
    print()
    print("  Nobody is listening on port 8000. Kill the server first.")
    print("  (Ctrl+C in the server terminal, then run this step.)")
    print()
    print("  ⏸  PAUSE & PREDICT: how is this different from 'wrong port'?")
    pause()
    print()

    try:
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("get_build_status", {"service_name": "auth-service"})
        print("      ❓  Unexpected success — is the server still running?")
    except Exception as e:
        print_error("Server down", e)

    print()
    print("  KEY INSIGHT: 'Server down' and 'wrong port' can produce the SAME")
    print("  error (Connection refused). Check the URL AND the process.")
    print()

    # ── Act 4: Recovery ──────────────────────────────────────────
    print("  ── Act 4: Recovery — Fix It ──────────────────────────────")
    print()
    print("  Now restart the server and re-run with the correct settings.")
    print()
    print("  ⏸  PAUSE & PREDICT: one interaction succeeds. Does the")
    print("     second call also succeed, or does the connection reset?")
    pause()
    print()

    try:
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                for service in ["auth-service", "payment-api"]:
                    result = await session.call_tool(
                        "get_build_status", {"service_name": service}
                    )
                    data = json.loads(result.content[0].text) if result.content else {}
                    status = data.get("status", "?")
                    print(f"      ✅  {service:<20}  {status.upper()}")
    except Exception as e:
        print_error("Recovery failed", e)

    print()
    print("  Recovery is the same code as the happy path.")
    print("  The error handling is in the APPLICATION LAYER — same principle")
    print("  as Week 4's execute_tool_safely().")
    print()

    print(BORDER)
    print("  THE MESSAGE: MCP connections fail in predictable, learnable ways.")
    print()
    print("  Wrong port     → ConnectionRefusedError — check the URL")
    print("  Wrong tool     → server-returned error — check the name")
    print("  Server down    → ConnectionRefusedError — check the process")
    print()
    print("  Senior take-home: these are NOT bugs. They are operational patterns.")
    print("  Your MCP client needs retry logic, timeout handling, and clear")
    print("  error messages — just like any other network dependency.")
    print()
    print("  YOUR TURN:")
    print("    • Start the server on a different port (edit mcp_server.py).")
    print("      What error changes?")
    print("    • Add a retry loop around Act 3 with max_retries=2 and 1s backoff.")
    print("      Does the model survive a brief server restart?")
    print("    • Call a tool with missing required args (omit service_name).")
    print("      What error do you get? Is it informative?")
    print(BORDER)


if __name__ == "__main__":
    asyncio.run(main())