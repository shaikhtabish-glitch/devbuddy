# Week 5 — The Context Protocol: Resources, Prompts, and Tools

**Goal:** Move beyond treating MCP as just another REST API for tools. Learn how to expose your proprietary environment—documents (Resources), standard workflows (Prompts), and actions (Tools)—so any generic AI client can instantly understand your architecture.

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

*(Note: The NodeJS server mirrors these architectural principles, but for this session, we will focus on the Python server as our primary Context provider).*

```bash
cd nodejs
git pull upstream main
npm install --legacy-peer-deps
```

---

## What You Have

Open `src/mcp_server.py`. Here's what's fundamentally different from Week 4. We are no longer just exposing `get_build_status` as a tool. We are exposing **Context**:
1.  **Resources:** The server exposes raw markdown files from `shared/data/`.
2.  **Prompts:** The server exposes standard organizational workflows (e.g., an Incident Analysis playbook).
3.  **Tools:** The server exposes functions that query the Week 3 RAG index (Qdrant).

## The Architecture: The Universal Interface

```
┌─────────────────────────┐         ┌─────────────────────────┐
│       MCP SERVER        │         │   UNIVERSAL AI CLIENT   │
│                         │         │ (Claude Desktop, Cursor)│
│  [Prompts]              │         │                         │
│   - Incident Playbook   │ ──────▶ │ 1. Fetch Prompts        │
│                         │         │                         │
│  [Resources]            │         │                         │
│   - API Specs           │ ──────▶ │ 2. Read Resources       │
│   - SLA Docs            │         │                         │
│                         │         │                         │
│  [Tools]                │         │                         │
│   - get_build_status()  │ ◀────── │ 3. Execute Tools        │
└─────────────────────────┘         └─────────────────────────┘
```

**The shift:** Your AI client doesn't need custom code to read your SLA docs or know your incident workflow. The server dictates the context.

---

## In-Session Steps

The moderator runs a demo first (stand up server + connect client). Watch, then follow these steps on your own machine.

### Step 0: Start the Server

```bash
# Terminal 1
cd python
source .venv/bin/activate
python src/mcp_server.py
# → Server running on http://localhost:8000/sse
```

### Step 1: Discovering Context (Resources & Prompts)

In a second terminal, explore how a client discovers context without hardcoded integrations.

```bash
python scripts/week-05/demo-01-wire-server.py
```
**The lesson:** Notice that the client didn't call a "tool" to read the SLA document. It navigated it as a `Resource`. It didn't hardcode a system prompt; it fetched the `Prompt` template directly from the server.

### Step 2: The Universal Client

```bash
python scripts/week-05/demo-02-cross-language.py
```
**The lesson:** This script simulates a "dumb" commercial client. It knows nothing about DevBuddy. By simply querying the server, it learns what workflows exist, reads the necessary files, and identifies the tools to execute. This proves that you can plug your MCP server into standard enterprise AI tools *today* with zero custom integration.

### Step 3: Protocol Errors & Resilience

```bash
python scripts/week-05/demo-03-break-it.py
```
**The lesson:** What happens when a client tries to read a file you haven't exposed as a Resource (like `/etc/passwd`)? The protocol strictly rejects it. You will learn to recognize and handle network-level rejections gracefully in your application layer.

### Step 4: Security & The Context Blast Radius

```bash
python scripts/week-05/demo-04-security-scope.py
```
**The lesson:** Exposing an entire filesystem as a Resource has a massive blast radius. If someone drops an API key in a folder exposed as a Resource, any connected commercial client can read it. You will learn the difference between the broad scope of Resources vs. the tight execution scope of Tools.

### Step 5: The Ecosystem Payoff

```bash
python scripts/week-05/demo-05-mcp-with-llm.py
```
**The lesson:** The grand finale. The LLM acts as the orchestrator. It fetches the system prompt from the server, reads a markdown specification from the server, and executes data-fetching tools on the server. True separation of Context from the Application layer is achieved.

---

## Acceptance Criteria
- [ ] `python src/mcp_server.py` starts without errors and connects to Qdrant.
- [ ] You can explain why exposing an SLA document as a `Resource` is architecturally superior to writing a custom `read_sla_doc()` Tool.
- [ ] You understand the security implications of exposing broad file-based Resources versus scoped Tools.
- [ ] The LLM in Demo 5 successfully synthesizes an answer using the server's Prompt, Resource, and Tool.

---

## Self-Learning (Before Week 6)

> **The take-home is building a Context Server.** You'll extend the MCP server with your own Context elements.

### Part A: Add a Custom Prompt & Resource
- Add a new `@mcp.prompt()` to `mcp_server.py` (e.g., a "Code Review" playbook).
- Add a new `@mcp.resource()` that exposes a specific code style guide from your local machine.
- Restart the server and verify they are discoverable via the `demo-01` script.

### Part B: Security Assessment
- Write a 1-paragraph security note:
  - What is the blast radius of the Resource you just exposed?
  - Could a malicious agent use path traversal (`../../`) to escape the directory? (Hint: test how `FastMCP` handles it).

### Part C: Real-World Integration
- Download the **Claude Desktop** application (if your organization permits).
- Configure its `claude_desktop_config.json` to connect to your Python MCP server.
- Ask Claude Desktop: *"Run the incident analysis workflow for payment-api."* Watch it natively fetch the prompt, read the SLA, and call your tools.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: mcp` | `pip install mcp` — check requirements.txt |
| Server starts but client can't connect | Ensure no other process is using port 8000 |
| `demo-05` returns generic LLM errors | Ensure `.env` has a valid `OPENROUTER_API_KEY` |
| RAG/Qdrant errors | Verify Qdrant is running: `docker-compose up -d` |
