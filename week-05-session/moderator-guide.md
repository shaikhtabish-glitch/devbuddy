# Week 5 — Moderator Guide: Write Once, Any Client Consumes It

> **Time:** 90 minutes. Hard stops at each timebox.
> **The theme:** *Week 4 gave the model hands — your tools, wired directly
> into your application. But if every team builds the same tools differently,
> you get 5 copies of get_build_status in 5 different formats. MCP
> standardises this: write a tool once, expose it on a server, and any
> client in any language consumes it.*
> **Key message:** MCP is an architectural shift from "my DevBuddy has tools"
> to "our org has a tool ecosystem." The protocol is the contract — not the
> language. The agent doesn't know (or care) whether a tool is local or remote.
> **Blueprint:** `docs/week-05.md` (setup, steps, acceptance criteria).
> **Pre-reading:** `docs/pre-reading-week-05.md`.
> **Plan:** `detailed-plan/week-5/` (README, engineer brief, moderator guide).

---

## The Arc You Are Teaching

| # | Demo | The line engineers take home |
|---|------|------------------------------|
| 0 | Tradeoffs | MCP has real overhead — if you don't have multiple consumers, just import the function |
| 1 | Wire server | Week 4 = hardcoded imports. Week 5 = dynamic discovery. The client asked "what tools exist?" |
| 2 | Advanced Client | Roots scope the workspace. Elicitation pauses for human input. Progressive discovery scales to 10k tools. |
| 3 | Break it | MCP connections fail in predictable, learnable ways. Wrong port, wrong tool, server down |
| 4 | Security & scope | Every tool is an attack surface. Start read-only. Add auth before write |
| 5 | MCP + LLM | The agent doesn't know tools are remote. Same Decide→Execute→Return loop from Week 4 |

**The thread from Week 4 → 5** (seniors respond to this): Week 4 boxed the
*actions* (tools). Week 5 makes those actions a *shared protocol*. Same reflex:
the framework gives a guarantee; the guarantee isn't the goal — the boundary
*you* own is. Now the boundary is a network boundary, and your security posture
moves with it.

**Senior take-home** — by the end each engineer can say, pointing at each
control, whose job it is:
- *What tools exist* → the SERVER decides, not the client
- *Whether a call succeeds* → my NETWORK and SERVER, not the model
- *Who can call my tools* → my AUTH and RATE LIMITS, not a prompt
- *What's exposed* → my REGISTRY, not the model
- *When not to use it* → no ecosystem = just import it

---

## Pre-Session Checklist (48 hours before)

- [ ] **Qdrant running:** `docker-compose up -d` from repo root →
      `curl http://localhost:6333/healthz` → `healthz check passed`.
- [ ] **LLM keys:** `OPENROUTER_API_KEY` in `python/.env`. Demos 00/03 are
      deterministic (no key); demos 01/02/04/05 connect to MCP server which
      uses the LLM for data synthesis.
- [ ] **MCP server tested:** `python src/mcp_server.py` starts without errors
      on port 8000. Verify: `curl http://localhost:8000/sse` returns a response.
- [ ] **Node.js MCP server tested (optional for cross-room testing):**
      `cd nodejs && node src/mcp_server.js` starts on port 3001.
- [ ] **All six demos rehearsed** from a clean state:
      `python scripts/week-05/demo-00-tradeoffs.py` … `demo-05-mcp-with-llm.py`.
- [ ] **Know your numbers:** demo-02 client-scaling requires understanding LLM token costs when it dynamically binds tools; demo-03 break-it assumes server on port 8000; demo-05 token
      costs are ~3–5 LLM calls per query.
- [ ] **Model nuance check:** the repo routes to `gpt-4o-mini` via OpenRouter.
      Extraction reliability varies — demo-01/05 may return slightly different
      status strings run to run. Never promise a fixed result. Print what happened.
- [ ] **Tests verified:** `python -m pytest tests/test_mcp_server.py -v` —
      checks imports, tool registration, callable locally.
- [ ] **Cross-machine test (optional):** two laptops running MCP servers can
      call each other's tools. Verify firewall/network aren't blocking port 8000.
- [ ] **Backup:** screen recording of each demo in case of live failure.
- [ ] **Ops team member** in the room as backup.

---

## The Demos You'll Run (all six)

**Demo 0 — Tradeoffs (`demo-00` · 3 min, no LLM, no network)**
1. Run it. It is instant — framing only.
2. *"MCP is an architecture, not a feature. Its value is sharing tools across
   teams; its cost is a network hop, a server to manage, and a new security
   boundary. Keep the 'when NOT to use it' list — you'll use it in the debrief."*
3. Emphasise the shift: Week 4 tools were private. Week 5 tools are shared.

**Demo 1 — Wire server (`demo-01` · 8 min)**
1. Prerequisites: Qdrant running, MCP server running on port 8000.
2. Run it. The client connects, discovers 3 tools (`list_tools()`), calls each.
3. *"Notice what changed from Week 4: tools are no longer imported. The client
   *asked* what tools exist and got an answer dynamically. No `from src.tools import`.
   A protocol replaced a hardcoded dependency."*
4. Point out: "The server is Python. The client is Python. But the protocol
   doesn't care. Now let's look at advanced client capabilities in demo-02.\"

**Demo 2 — Advanced Client Patterns (`demo-02` · 8 min)**
1. Prerequisites: Python server on 8000, and OPENROUTER_API_KEY in .env.
2. Run it. The script demonstrates Roots, Elicitation (simulated), and Progressive Tool Discovery.
3. *"10,000 schemas would blow up the context window. We start the LLM with ONE meta-tool: search_tools."*
4. Watch the terminal as the client dynamically discovers `get_build_status` and injects its schema into the LLM context mid-loop.

**Demo 3 — Break it (`demo-03` · 10 min, deterministic)**
1. Prerequisites: MCP server on port 8000.
2. Act 1: wrong port (9999) → ConnectionRefusedError. Act 2: wrong tool name
   (`get_buildstatus`) → server-returned error. Act 3: server down →
   ConnectionRefusedError. Act 4: fix it → success.
3. *"These are NOT bugs. They are operational patterns. Your MCP client needs
   retry logic, timeout handling, and clear error messages — just like any
   other network dependency."*
4. Key insight: same ConnectionRefusedError for "wrong port" AND "server down"
   — you need to distinguish by checking the URL AND the process.

**Demo 4 — Security & scope (`demo-04` · 8 min)**
1. Prerequisites: MCP server on port 8000.
2. Connects, lists all tools, runs a security assessment on each: read-only?
   auth? rate-limited? blast radius?
3. *"The model proposes a tool call. Your app layer validates it. The model
   proposes a connection. Your server auth validates it. Same principle as
   Week 4, one layer out."*
4. Show `delete_incident_record` (if present in mcp_server.py) — a WRITE tool
   that requires an auth token. *"Even with auth, does your team want this
   exposed? That's the conversation."*

**Demo 5 — MCP + LLM (`demo-05` · 10 min)**
1. Prerequisites: Qdrant running, MCP server on port 8000.
2. The LLM discovers MCP tools, decides which to call, MCP executes, LLM answers.
3. *"This is the EXACT same Decide→Execute→Return loop from Week 4. The LLM
   doesn't know — and doesn't care — whether tools are local functions or
   remote MCP endpoints."*
4. PAUSE & PREDICT: "How many tools will the LLM call for 'Is payment-api
   healthy and what were its last 2 deployments?'"
5. YOUR TURN: "Swap the MCP URL to your partner's server. Does the LLM notice?"

---

## Session Script

### 0:00–12:00 — Framing (12 min)

1. **Open (2 min):** "Last week you gave the model tools — functions it could
   request. But what happens when the next team needs `get_build_status`?"
   → They write it again. 5 copies. 5 different formats.
2. **The Week 4 problem → MCP solution (4 min):**
   *"MCP is an open standard. Server exposes tools. Client discovers them.
   Write once. Any client in any language consumes it."*
   Draw the architecture:
   ```
   MCP Server (your APIs) ← MCP Client (DevBuddy) ← LLM
   ```
3. **Server vs client (2 min):** "Server holds the tools. Client connects and
   discovers (`list_tools()`). Protocol is standard JSON-RPC. Any language."
4. **The shift (2 min):** "Week 4 = `from src.tools import get_build_status`.
   Week 5 = `session.list_tools()` → 'get_build_status found!'. No import.
   Dynamic discovery. That's the difference."
5. **Run demo-00 (2 min):** the tradeoffs board. Call out "when NOT to use"
   explicitly.

**Time check at 12:00. Move to live demos.**

### 12:00–52:00 — Live demos + hands-on (40 min)

**Step 1: demo-01 live (8 min) — YOU.** Start the MCP server. Connect client.
Discover tools. Call one. *"The client imported NOTHING. It asked what tools
exist and got an answer. That's the shift."*

**Step 2: Everyone starts their MCP server (8 min) — ENGINEERS.**
1. `docker-compose up -d` (if not running).
2. `python src/mcp_server.py` in one terminal.
3. `python scripts/week-05/demo-01-wire-server.py` in another.
Walk around. *Common issues:* Qdrant not running, wrong port, `.env` missing.

**Step 3: demo-02 live (6 min) — YOU.** Advanced Client Patterns. Run the script.
*"Watch the LLM search for a tool, and watch the client dynamically inject the schema."*
Discuss why Roots (workspace scoping) and Elicitation (human-in-the-loop auth) are critical for enterprise adoption.

**Step 4: demo-03 live (8 min) — YOU.** Break it: wrong port, wrong tool name,
server down, recovery. Then have them run it themselves. *"These are the error
messages you'll see on-call. Learn them now."*

**Step 5: demo-04 live (6 min) — YOU.** Security assessment walkthrough.
*"Every tool is an attack surface. Start read-only. Add auth before write."*

**Step 6: Demo-05 live (4 min) — YOU.** MCP + LLM. *"The agent doesn't know
tools are remote. Swap the URL and it never notices. That's the ecosystem."*

**Time check at 52:00. Move to explore + debrief.**

### 52:00–68:00 — Explore + cross-room (16 min)

**Step 7: Cross-room call (8 min).**
1. "Find a partner. Get their server address (IP:8000/sse)."
2. "Connect your client to their server. Call their tools."
3. "Ecosystem achieved. Their DevBuddy can use your tools. Yours can use theirs."
4. If on same machine: "Start two MCP servers on different ports and connect
   to both."

**Step 8: Add your own tool (8 min).**
1. "Add a tool to `mcp_server.py`. Any tool. `get_server_time()`, `get_user()`,
   whatever."
2. "Restart the server. Does `list_tools()` show it? Call it. Does it work?"
3. "Every team can add their own tools to the shared server. No copy-paste."

### 68:00–90:00 — Debrief (22 min)

1. **Ecosystem (5 min).** "Who successfully called a partner's tool? What was
   the hardest part of the connection? How is this different from 'my DevBuddy
   has tools' in Week 4?"
2. **Security (5 min).** "What's the worst thing someone could do if they
   reached your MCP server? What would you add before production?"
   → auth, rate limiting, read-only defaults, audit logging.
3. **Enterprise Readiness (4 min).** "Why do we need Roots? Why do we need Progressive Discovery?"
   → Context windows are finite. We must bind tools at runtime."
4. **When NOT to use MCP (4 min).** "If you have one team, one tool, no
   sharing — just import it (Week 4 style). MCP overhead isn't free."
5. **Preview Week 6 (4 min).** "Next week: Agentic workflows. We chain Weeks
   2–5 into one autonomous pipeline. The MCP server you built today is what
   the agent calls." Self-learning Parts A–D due before then.

---

## Common Pitfalls & Recovery

| Situation | Recovery |
|-----------|----------|
| **Qdrant not running** | `docker-compose up -d` from repo root; `curl localhost:6333/healthz`. MCP server won't start without it. |
| **MCP server doesn't start** | Check Qdrant first. Then check `.env` has `OPENROUTER_API_KEY`. Port 8000 already in use? Kill the process. |
| **Client can't connect to server** | Check URL (`http://127.0.0.1:8000/sse`). Wrong port? Server running? |
| **Tool returns `unknown` instead of data** | RAG extraction depends on chunk quality. Try `service_name=auth-service` first — it has the richest data. |
| **Client-scaling demo fails** | Missing OPENROUTER_API_KEY? The LLM orchestration loop requires API access. |
| **demo-03 Act 3 (server down) doesn't fail** | Server is still running. Kill it (`Ctrl+C`). The error should change from "tool works" to "connection refused". |
| **LLM doesn't call any tools (demo-05)** | Tool descriptions may be too vague. The conversion from MCP schema to LangChain may lose precision. |
| **Token costs higher than expected** | Each demo-05 round is a full LLM call. Results re-enter context. This IS the lesson — cost compounds. |
| **Node.js server deps missing** | `cd ../nodejs && npm install --legacy-peer-deps`. |
| **Cross-room call fails** | Firewall blocking port 8000? Different machines on the same network? Use `localhost` if on same machine with different ports. |
| **Demo runs over time** | Cut Step 7 (cross-room) or Step 8 (add your own tool). Never cut the debrief — that's where the senior take-home solidifies. |

---

## Post-Session Checklist

- [ ] Runbook `week-05.md` updated: client scaling observations, security notes, ADR seed
- [ ] Channel message: classroom assignment (48 h) + self-learning Parts A–D (before Week 6)
- [ ] Encourage the **MCP eval** run (`shared/evals/week-05-mcp-tool-ecosystem.yaml`)
- [ ] Note model-behaviour drift / demo flakiness for ops before the rerun
- [ ] Cross-room test results: which teams were able to call each other's servers?

---

## Language Quick-Reference

| | Python | Node.js |
|---|--------|---------|
| MCP Server | `src/mcp_server.py` (FastMCP) | `nodejs/src/mcp_server.js` (SDK + Express) |
| Transport | SSE on port 8000 | SSE on port 3001 |
| Tools | `get_build_status`, `get_recent_deploys`, `get_active_incidents` | same 3 tools, identical schemas |
| Client demos | `scripts/week-05/demo-01-wire-server.py` | `scripts/week-05/demo-01-mcp-client.js` |
| Advanced Client | `demo-02-client-scaling.py` (Roots, Discovery) | (Not demonstrated in Node.js path) |
| Tests | `tests/test_mcp_server.py` | `tests/test_mcp_server.js` |

Both servers expose the same 3 RAG-powered tools. Same protocol (JSON-RPC over SSE).
Same schemas. Different languages — that's the MCP promise.