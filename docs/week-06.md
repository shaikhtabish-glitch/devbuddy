# Week 6 — Agentic Workflows

**Goal:** Chain Weeks 2–5 into an autonomous pipeline. Retrieve context, call tools, produce structured output, decide next step — all in one flow.

---

## Setup

```bash
cd python
source .venv/bin/activate
git pull upstream main
pip install -r requirements.txt   # langgraph>=0.2.0 should be installed

# Qdrant must be running
docker-compose up -d

# Index the documents (safe to run multiple times — skips if already indexed)
python -c "from src.rag import index_documents; index_documents()"
```

Verify you're ready:

```bash
python -m pytest tests/ -v -k "not analyze_pr and not run_tool_loop"
```

---

## What You Have

Open `src/agent.py`. It's already fully built — 6 nodes, a dynamic router with
anti-cascade logic, cost tracking, a step/cost guard, and both fixed-chain and
dynamic agent builders. It composes everything from Weeks 2–5:

```
agent.py
├── from src.llm import get_llm          # Week 1
├── from src.rag import retrieve         # Week 3 (RAG)
├── MCP session (spawns mcp_server.py)   # Week 5 (tools via MCP)
└── LangGraph StateGraph                 # orchestrator
```

Tools are called through the MCP server from Week 5 — no direct imports from
`src.tools`. The agent spawns `mcp_server.py` as a subprocess for each tool call.
This is simple and reliable — MCP's stdio transport manages its own lifecycle.

**The import graph is now complete.** Every module built so far feeds into the agent.

## Files You'll Touch
- `src/agent.py` — the orchestrator (imports llm, rag, spawns MCP server)
- `scripts/week-06/` — demo scripts

---

## In-Session Steps

The moderator runs a demo first (fixed chain: RAG → tool → structured output). Watch, then follow these steps.

> ⚠️ This is the most complex hands-on so far. Pair up if stuck. The agent WILL break — that's the point.

---

### Step 1: Study and run the fixed chain (15 min)

`src/agent.py` is already built. Open it and study the architecture:

- **State:** `AgentState` carries query, service_name, context, build_status, deploys, incidents, report, steps, cost
- **Nodes:** `extract_service` → `retrieve_context` → `check_build` → `check_deploys` → `check_incidents` → `generate_report`
- **Tools** are called via MCP (`_call_mcp_tool()`) — spawns the Week 5 server
- **Fixed chain:** `build_fixed_chain()` — 4 steps, always the same path
- **Dynamic agent:** `build_dynamic_agent()` — model decides steps at runtime

Run the fixed chain:

```bash
python scripts/week-06/demo-01-fixed-chain.py
```

The chain: extract service → retrieve → check build → report. 4 steps every time.
Notice: it checks the RIGHT service (extracted from the query), but the path is rigid.
If you added a `check_deploys` node, the fixed chain couldn't use it.

---

### Step 2: Run the dynamic agent (10 min)

```bash
python scripts/week-06/demo-02-dynamic-routing.py
```

The dynamic agent adapts to each query:
- *"Is payment-api healthy?"* → retrieve + check_build + report (3 steps)
- *"What was deployed and any incidents?"* → retrieve + check_deploys + check_incidents + report (4 steps)
- *"Full readiness assessment"* → all 4 data steps + report (5 steps)

**Key insight:** The router only runs steps the query explicitly asks for. It won't
cascade — "healthy?" doesn't trigger "also check incidents." This keeps costs
proportional to the query complexity.

---

### Step 3: Break it — test the guard (5 min)

Open `src/agent.py`. Find the guard function:

```python
MAX_STEPS = 10
MAX_COST = 2.00
```

Change `MAX_STEPS` to `2`. Run a query that needs 3+ steps:

```python
from src.agent import run_dynamic_agent
result = run_dynamic_agent("Give me a full readiness assessment for payment-api")
print(result["steps"])  # → 2 (stopped by guard)
```

The agent stops before completing. **Guards prevent runaway agents** — essential
for production where every step costs money.

Change `MAX_STEPS` back to `10` when done.

---

### Step 4: Extend — add a new tool (optional, 10 min)

Add a new tool to `src/mcp_server.py` (like `get_service_owner`), then add a
corresponding node in `agent.py`. Add the node to `build_dynamic_agent()` and
the router's decision list. Restart and test — the agent now has a new capability.

---

### Step 5: Explore (remaining time)

```bash
# Study the agent implementation
cat src/agent.py

# Run the demos
python scripts/week-06/demo-01-fixed-chain.py      # fixed vs broken
python scripts/week-06/demo-02-dynamic-routing.py   # dynamic adaptation
python scripts/week-06/demo-03-conversational-agent.py  # talk to DevBuddy
```

---

## Acceptance Criteria
- [ ] Fixed chain (extract → retrieve → build → report) runs end-to-end via demo-01
- [ ] Dynamic agent adapts to 3 different queries with different step counts via demo-02
- [ ] Guard stops the agent when `MAX_STEPS` is lowered to 2
- [ ] You can trace cost per step and total cost for a query
- [ ] You can explain: *"Fixed chains are predictable but brittle. Dynamic routing adapts but costs more."*

---

## Self-Learning (Before Week 7)

> **The take-home is dynamic routing + state management.** Fixed chains work. Dynamic routing adapts. Both have tradeoffs.

### Part A: Build both, compare cost
- Build a fixed 3-step chain and a dynamic router for the same task
- Run 5 different queries through both
- Compare: steps taken, LLM calls made, total cost
- Which approach wins for each query type? When is fixed better? When is dynamic worth the extra cost?

### Part B: Coherence stress test
- Run a complex query that requires 4+ steps
- Document: did the agent repeat itself? Forget context? Pursue an irrelevant path?
- What state management strategy would fix it? (Truncation? Summarisation? Different state format?)

### Part C: Design an orchestrator
- Sketch an orchestrator + sub-agent architecture for a real workflow:
  - "PR review → check affected services → generate deployment risk report"
- Which steps are sub-agents? Which are tools? Where does the human approve?

### Part D: Capstone preview
- Read `detailed-plan/capstone/README.md` — this is what you'll build between now and the presentation
- Which components from Weeks 2–6 will you integrate? What's your architecture?

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ImportError: langgraph` | `pip install langgraph` |
| Agent loops infinitely | The guard is already there — `MAX_STEPS=10`, `MAX_COST=$2.00` |
| Router always picks the same step | Improve the routing prompt. Make decision criteria explicit. |
| MCP tool call fails | Ensure Qdrant is running (`docker-compose up -d`) and index exists |
| State not carrying between steps | Check that each node returns the state dict |

---

## Runbook Contribution

Write a 1-paragraph ADR: "We chose [fixed-chain / dynamic-routing] for our agent because…"
