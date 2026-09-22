# Week 5 — MCP: DevBuddy Joins an Ecosystem

**Goal:** Move from one-off custom tools to a shared, reusable layer. Write tools once. Expose them over MCP. Any team's DevBuddy consumes them.

---

## Setup

### Python

```bash
cd python
source .venv/bin/activate
git pull upstream main
pip install -r requirements.txt   # mcp>=1.0.0 should be installed

# Qdrant must be running (Week 3+)
docker-compose up -d
```

### Node.js

```bash
cd nodejs
git pull upstream main
npm install --legacy-peer-deps   # @modelcontextprotocol/sdk should be installed

# Qdrant must be running (Week 3+)
docker-compose up -d
```

Verify you're ready:

**Python:**

```bash
python -m pytest tests/test_mcp_server.py -v
```

**Node.js:**

```bash
npx vitest run tests/test_mcp_server.js
```

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
# Python
python src/mcp_server.py
# → Server running on http://localhost:8000/sse

# Node.js
node src/mcp_server.js
# → Server running on http://localhost:3001/sse
```

The server indexes documents from `shared/data/` once at startup, then serves
tools that query that index. No mock data. No repeated indexing.

---

### Step 2: Connect a client and call a tool (10 min)

Open a second terminal. Use the MCP client to connect, discover, and call:

```bash
python scripts/week-05/demo-01-wire-server.py
```

This script walks through discovery (`list_tools()`), then calls all three tools
(`get_build_status`, `get_recent_deploys`, `get_active_incidents`) against real
data from the RAG index.

**The story:** DISCOVER → QUERY → RESPONSE. The MCP protocol in action.
All data from the RAG index (Week 3), served over a shared protocol (Week 5).
In Week 4 tools were hardcoded imports. Here, the client asks "what tools exist?"
and gets an answer dynamically. No import. No shared code. A protocol.

---

### Step 3: Debug — break the connection (10 min)

Misconfigure intentionally to learn the error patterns:

```bash
python scripts/week-05/demo-03-break-it.py
```

This script walks through 4 acts: wrong port, wrong tool name, server down,
and recovery. Each act shows the exact error message you'd see in production.

**These are the most common production issues.** You're debugging MCP connections.
Learn the error messages — you'll see them again.

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

### Step 5: Cross-Language MCP — same protocol, any language (10 min)

MCP is language-agnostic. The Python server exposes tools. A Node.js client
can call them. A Java client can call them. The protocol IS the contract —
not the language.

```bash
# Terminal 1: Python MCP server
python src/mcp_server.py
# → http://localhost:8000/sse

# Terminal 2: Node.js MCP server
cd ../nodejs && node src/mcp_server.js
# → http://localhost:3001/sse

# Terminal 3: Cross-language demo
python scripts/week-05/demo-02-cross-language.py
```

This connects a Python client to BOTH servers and compares the tool schemas.
Identical names. Identical JSON. Different languages, same protocol.

**Senior take-home:** the language of your server is an internal implementation
detail. The protocol — tool names, schemas, JSON responses — is your public
API. Version that, not the code.

---

### Step 6: MCP + LLM — the agent doesn't know tools are remote (10 min)

The Decide → Execute → Return loop from Week 4 is IDENTICAL when tools come
from MCP. The LLM doesn't know — and doesn't care — whether a tool is a local
function or a remote MCP endpoint.

```bash
python scripts/week-05/demo-05-mcp-with-llm.py
```

**Key insight:** You can swap the MCP server URL to a different team's server
and the LLM never notices. That's the ecosystem payoff.

### Step 7: Security & scope — what does your MCP server expose? (10 min)

Your MCP server is now reachable over the network. Anyone who can connect can
discover your tools. Before you ship it, audit the blast radius.

```bash
python scripts/week-05/demo-04-security-scope.py
```

This script inspects each tool's schema, assesses read-only vs write posture,
and walks through a hardening checklist: auth, rate limiting, audit logging.

**Senior take-home:** Same principle as Week 4, one layer out. The model
proposes a tool call. Your app layer validates it. The model proposes a
connection. Your server auth validates it.

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

### Part D: Cross-language test
- The Node.js MCP server (`nodejs/src/mcp_server.js`) exposes the same tools
- Try connecting a Python MCP client to the Node.js server, or vice versa
- Does tool discovery work across languages? Does tool calling?
- This is the promise of MCP — write once, consume anywhere.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: mcp` (Python) | `pip install mcp` — check requirements.txt |
| `ERR_MODULE_NOT_FOUND: @modelcontextprotocol/sdk` (Node.js) | `npm install --legacy-peer-deps` from `nodejs/` |
| Server starts but client can't connect | Are you using the right transport? stdio vs SSE? |
| `call_tool` returns error | Check tool name matches exactly (case-sensitive) |
| Server hangs | Python: ensure `asyncio.run(main())` at bottom. Node.js: ensure `server.connect()` is called. |
| MCP tools need LLM access | Ensure `.env` has `OPENROUTER_API_KEY` — tools use the LLM for data synthesis |

---

## Runbook Contribution

Write a 1-paragraph ADR: "We chose to expose `get_build_status` via MCP rather than a bespoke REST endpoint because…"
