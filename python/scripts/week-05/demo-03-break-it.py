"""
Demo 3: Protocol Errors & Resilience

THE POINT OF THIS DEMO: MCP connections fail in predictable ways.
Since you are now requesting Context over a network, you must handle
network errors, missing resources, and missing tools.
These are operational patterns, not bugs.

Prerequisites:
  MCP server running on port 8000:
    python src/mcp_server.py

Run: python scripts/week-05/demo-03-break-it.py
"""
import os, sys, asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.client.sse import sse_client
from mcp import ClientSession

MCP_URL = "http://127.0.0.1:8000/sse"
BORDER = "=" * 70

def print_error(error: Exception) -> None:
    msg = str(error)
    key = type(error).__name__
    print(f"  [OUTPUT] ← ❌ [{key}] {msg[:120]}")
    print()

def pause(prompt: str = "  ⏸  Press Enter to continue… ") -> None:
    try:
        input(prompt)
    except EOFError:
        print()

async def main():
    print(BORDER)
    print("  Demo 3: Protocol Errors & Resilience")
    print(BORDER)
    print()
    print("  When you shift to an ecosystem model, failure handling moves")
    print("  from Try/Catch blocks to Application Layer Routing.")
    print()

    # ── Act 1: Resource Not Found ──────────────────────────────────
    print("  ── Act 1: Requesting a missing Resource ──────────────────")
    print("  Client asks for a file that isn't exposed or doesn't exist.")
    print()
    
    target_uri = "file:///etc/passwd"
    print(f"  [INPUT]  → session.read_resource('{target_uri}')")
    
    try:
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # Server only exposes shared/data/*
                await session.read_resource(target_uri)
                print("  [OUTPUT] ← ❓ Unexpected success")
                print()
    except Exception as e:
        print_error(e)
    
    print("  KEY INSIGHT: The server explicitly rejected this. Path traversal")
    print("  is blocked by the protocol mapping.")
    print()
    pause()

    # ── Act 2: Tool Not Found ──────────────────────────────────────
    print("  ── Act 2: Requesting a missing Tool ──────────────────────")
    print("  Client attempts to execute a legacy tool name.")
    print()
    
    tool_name = "get_buildstatus" # intentionally misspelled
    tool_args = {"service_name": "auth-service"}
    print(f"  [INPUT]  → session.call_tool('{tool_name}', {tool_args})")
    
    try:
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await session.call_tool(tool_name, tool_args)
                print("  [OUTPUT] ← ❓ Unexpected success")
                print()
    except Exception as e:
        print_error(e)
        
    print("  KEY INSIGHT: Unknown tool errors come from the SERVER.")
    print("  The client must gracefully handle this and perhaps ask the LLM")
    print("  to re-plan using `list_tools()`.")
    print()
    pause()

    # ── Act 3: Connection Error ────────────────────────────────────
    print("  ── Act 3: Server Offline ─────────────────────────────────")
    print("  Client attempts to connect to a server that isn't running.")
    print()
    
    bad_url = "http://127.0.0.1:9999/sse"
    print(f"  [INPUT]  → connecting to '{bad_url}'")
    
    try:
        async with sse_client(bad_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("  [OUTPUT] ← ❓ Unexpected success")
                print()
    except Exception as e:
        print_error(e)
        
    print("  KEY INSIGHT: Connection errors happen at the transport layer,")
    print("  before MCP even initializes. Your client needs retry logic with")
    print("  exponential backoff.")
    print()
    pause()
    
    print(BORDER)
    print("  THE MESSAGE: The protocol enforces strict contracts. Your AI orchestrator")
    print("  must be built to handle these rejections gracefully, dynamically")
    print("  re-querying the context server when resources or tools shift.")
    print(BORDER)

if __name__ == "__main__":
    asyncio.run(main())