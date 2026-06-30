# Week 5 — MCP: DevBuddy Joins an Ecosystem

**Goal:** Move from one-off custom tools to a shared, reusable layer. Write tools once. Expose them over MCP. Any team's DevBuddy consumes them.

---

## Setup

```bash
cd python
source .venv/bin/activate
git pull upstream main
pip install -r requirements.txt   # mcp>=1.0.0 should be installed

# Qdrant must be running (Week 3+)
docker-compose up -d
```

Verify you're ready:

```bash
python -c "import mcp; print('MCP SDK OK')"
python -m pytest tests/test_tools.py -v -k "not run_tool_loop"
```

---

## What You Have

Open `src/mcp_server.py`. It uses FastMCP to expose 3 tools — but here's what's
different from Week 4: these tools don't use hardcoded mock data. They query the
**Week 3 RAG index** (Qdrant) and synthesise results with the LLM. One data source,
many consumers. By the end of this session, you'll understand why that matters.

## The Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌─────┐
│   MCP Server     │ ←── │   MCP Client     │ ←── │ LLM │
│  (your tools)    │     │  (DevBuddy)      │     │     │
│                  │     │                  │     │     │
│ get_build_status │     │ 1. Discover tools│     │     │
│ get_recent_      │     │ 2. Model decides │     │     │
│   deploys        │     │ 3. Client calls  │     │     │
│ get_active_      │     │    server        │     │     │
│   incidents      │     │ 4. Returns result│     │     │
└──────────────────┘     └──────────────────┘     └─────┘
```

**Write once. Consume anywhere.** Python, Node.js, Java — any MCP client can use your tools.

## Files You'll Touch
- `src/mcp_server.py` — the MCP server (imports `src.rag` for RAG data, `src.llm` for synthesis)
- `src/rag.py` — already built (Week 3 vector store — tools query it directly)
- `src/llm.py` — already built (Week 1 OpenRouter client)
- `scripts/week-05/` — demo scripts

---

## In-Session Steps

The moderator runs a demo first (stand up server + connect client). Watch, then follow these steps on your own machine.

---

### Step 1: Study the MCP server (10 min)

Open `src/mcp_server.py`. Walk through the architecture:

```python
from mcp.server.fastmcp import FastMCP
from src.rag import retrieve, index_documents   # Week 3 RAG
from src.llm import get_llm                      # Week 1 client

mcp = FastMCP("devbuddy-mcp")

# Shared helper — every tool follows this pattern
def _synthesise(instructions, query, k=5):
    chunks = retrieve(query, k=k)       # ← hits Qdrant, not hardcoded dicts
    # feed chunks to LLM → returns JSON

@mcp.tool()
def get_build_status(service_name: str) -> str:
    return _synthesise(
        "Extract the current build/health status...",
        f"{service_name} build status health check deploy",
    )
```

**Key insight:** The `@mcp.tool()` decorator registers the function with FastMCP.
Under the hood, each tool retrieves chunks from the Week 3 Qdrant index and
synthesises a JSON result with the LLM. Same RAG pipeline, new consumer.

Start it:

```bash
# Qdrant must be running first: docker-compose up -d
python src/mcp_server.py
# → RAG index ready: 19 chunks indexed
# → Server running on stdio. Waiting for client connections...
```

The server indexes documents from `shared/data/` once at startup, then serves
tools that query that index. No mock data. No repeated indexing.

---

### Step 2: Connect a client and call a tool (10 min)

Open a second terminal. Use the MCP client to connect and call:

```python
# scripts/week-05/demo-01-mcp-client.py
import asyncio
from mcp.client.stdio import stdio_client
from mcp import ClientSession

async def main():
    async with stdio_client("python src/mcp_server.py") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Discover available tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools]}")

            # Call get_build_status
            result = await session.call_tool("get_build_status", {"service_name": "payment-api"})
            print(f"Result: {result}")

asyncio.run(main())
```

```bash
python scripts/week-05/demo-01-mcp-client.py

  📡  DISCOVER: list_tools()
      🏗️  get_build_status
          Return the current build/health status for a given service.
      🚀  get_recent_deploys
          Return the last N deployments for a given service.
      🚨  get_active_incidents
          Return any active (unresolved) incidents for a given service.

  ───────────────────────────────────────────────────────────
  🏗️  QUERY: get_build_status
  ───────────────────────────────────────────────────────────
      →  RESPONSE  auth-service:  HEALTHY
                     last deploy  2026-06-28T08:15:00Z
      →  RESPONSE  payment-api:   DEGRADED
                     last deploy  2026-06-28T06:45:00Z

  ───────────────────────────────────────────────────────────
  🚀  QUERY: get_recent_deploys(payment-api, limit=2)
  ───────────────────────────────────────────────────────────
      →  ✅  abc123def456  tabish   2026-06-28T08:15:00Z
      →  ✅  def789ghi012  maria    2026-06-28T06:45:00Z

  ───────────────────────────────────────────────────────────
  🚨  QUERY: get_active_incidents(payment-api)
  ───────────────────────────────────────────────────────────
      →  Sev1    INC-842
                  payment-api latency spike. 15% affected.

  All data from the Week 3 RAG index (Qdrant).
  Same tools as Week 4. Any MCP client can call them.
```

**The story:** DISCOVER → QUERY → RESPONSE. The MCP protocol in action.
All data from the RAG index (Week 3), served over a shared protocol (Week 5).

---

### Step 3: Debug — break the connection (10 min)

Misconfigure intentionally to learn the error patterns:

```bash
# Wrong transport — try connecting to HTTP instead of stdio
python -c "
from mcp.client.sse import sse_client
# This will fail — server is on stdio, not SSE
"

# Wrong tool name
python -c "
# Call 'get_buildstatus' instead of 'get_build_status'
# → Tool not found error
"
```

**These are the most common production issues.** You're debugging MCP connections. Learn the error messages — you'll see them again.

---

### Step 4: Add your own tool (10 min)

Add a new tool to the server. Any tool:

```python
# In mcp_server.py, add before the entry point:
@mcp.tool()
def get_server_time() -> str:
    """Return the current server time."""
    from datetime import datetime
    return datetime.now().isoformat()
```

Restart the server. Reconnect the client. Does `list_tools()` show your new tool? Call it. Does it work?

**Every team can add their own tools to the shared server.** No copy-paste. No duplication. One source of truth.

---

### Step 5: stdio vs production (5 min)

Our server uses **stdio** transport — the client spawns `python src/mcp_server.py`
as a subprocess. This is perfect for local dev, but it has two limitations:

1. **New process per connection** — no shared state, no connection pooling
2. **Same machine only** — stdio can't cross the network

In production you'd switch to **HTTP/SSE** transport — the server runs as
a long-lived daemon on a port, clients connect over the network:

```python
# Production pattern (not used in this session):
if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
```

Same tools. Same protocol. Different transport. That's the MCP promise.

---

### Step 6: Explore (remaining time)

```bash
# Study the server implementation
cat src/mcp_server.py

# Run the full pipeline: MCP tools → LLM
cat scripts/week-05/demo-02-mcp-with-llm.py
```

---

## Acceptance Criteria
- [ ] `python src/mcp_server.py` starts without errors
- [ ] Client connects and `list_tools()` shows all registered tools
- [ ] `call_tool("get_build_status", {"service_name": "payment-api"})` returns a result
- [ ] Changing the tool name produces a clear error (not a crash)
- [ ] You can explain: *"MCP takes our Week 4 tools and makes them available to any client, in any language."*

---

## Self-Learning (Before Week 6)

> **The take-home is the shared ecosystem.** You'll extend the MCP server with your own tool and think through security.

### Part A: Add your own tool
- Add a new tool to the MCP server — not from `src/tools.py`, something you write
- Ideas: `get_current_time()`, `get_user_info(name)`, a tool that reads a file, a tool that queries an API
- Document it: tool name, description, parameters, what it returns

### Part B: Security assessment
- Write a 1-paragraph security note for your new tool:
  - What does it expose? Is it read-only?
  - What's the blast radius if called with bad arguments?
  - What auth/rate-limiting/logging would you add before production?

### Part C: MCP vs REST decision
- Compare your MCP tool to an equivalent REST endpoint
- When would you use MCP? When would plain REST be simpler?
- Write a decision heuristic: "Use MCP when ___. Use REST when ___."

### Part D: Cross-language test (optional)
- If you have Node.js installed, try connecting to the Python MCP server from a Node.js MCP client
- Does tool discovery work across languages? Does tool calling?
- This is the promise of MCP — write once, consume anywhere.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: mcp` | `pip install mcp` — check requirements.txt |
| Server starts but client can't connect | Are you using the right transport? stdio vs SSE? |
| `call_tool` returns error | Check tool name matches exactly (case-sensitive) |
| Server hangs | Ensure `asyncio.run(main())` is at the bottom of the file |

---

## Runbook Contribution

Write a 1-paragraph ADR: "We chose to expose `get_build_status` via MCP rather than a bespoke REST endpoint because…"
