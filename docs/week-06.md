# Week 6 — Agentic Workflows

**Goal:** Compose Weeks 1–5 into an autonomous agent — and make it *know when to stop*.
An agent is a state machine over contracts you already own: typed state, explicit
transitions, guards that refuse to paper over missing data.

---

## Setup

### Python (reference implementation)

```bash
cd python
source .venv/bin/activate
pip install -r requirements.txt

# Terminal 1: Qdrant (Week 3+)
docker-compose up -d
python -c "from src.rag import index_documents; index_documents()"

# Terminal 2: MCP server (Week 5) — tools + resources + prompts on :8000
python src/mcp_server.py
# → http://127.0.0.1:8000/sse
```

### Node.js

```bash
cd nodejs
npm install --legacy-peer-deps

# MCP server on :3001 (ports intentionally differ from Python — see Troubleshooting)
node src/mcp_server.js
# → http://localhost:3001/sse
```

### Verify you're ready

```bash
python -m pytest tests/test_agent.py -v
```

Unit tests (state, guards, registry, refusal) run anywhere. Integration tests are
marked `skipif` — they tell you exactly which service they couldn't reach instead
of erroring. All green with services up = fully verified.

---

## What You Have

Open `src/agent.py`. The composition is real — and checkable:

```
agent.py
├── from src.llm import get_llm                 # Week 1 — provider
├── from src.schemas import AgentAnswer, …      # Week 2 — contracts; THEIR
│                                                #   validators run on the
│                                                #   agent's own output
├── from src.rag import retrieve                # Week 3 — local retrieval backend
└── THE SEAM — one config flip, same code (TOOL_BACKEND=mcp | local)
      ├── call_tool(name, args, contract=…)     # tools
      │     ├── mcp   → Week 5 server :8000 — search_docs, get_build_status,
      │     │           get_recent_deploys, get_active_incidents
      │     └── local → Week 4 src.tools in-process (execute_tool_safely)
      ├── read_resource(filename)              # Week 5 RESOURCES: file://shared/data/*
      └── get_prompt(name, args)               # Week 5 PROMPTS: incident_analysis_prompt
```

Everything below derives from **one dict**, `NODE_REGISTRY` — they cannot drift apart:

| Derived from the registry | Where it shows up |
|---|---|
| Router's step catalog | the prompt the model sees |
| Graph's route map | `PLAN_ROUTE_MAP` (conditional edges) |
| Guard's requirements | `REQUIREMENTS` per query category |
| Refusal message | built from registry keys, never from the model |

### The three guards

| Guard | Kind | Job |
|---|---|---|
| `budget_guard` | operational | steps/cost ceiling; on trip still emits a **typed** blocked answer without another LLM call |
| `plan` | structural | LLM **proposes**, code **disposes**: imperative actions refused before any LLM call, unknown capabilities refused via the registry, repeats corrected once then handed to the guard |
| `validate` | business | required state (derived from the query category) must be present — and the build must not be `down` — **before** `generate_report`; writes the blocked report itself, deterministically |

### The checkpoints

| CP | Concept | Demo | What you'll see |
|----|---------|------|-----------------|
| **C1** | Fixed chain | `demo-01` | 4 steps, typed state flowing, structured report + recorded audit trail |
| **C2** | Missing-step hallucination | `demo-04` | node removed → naive report invents build data from `BUILD: {}` — then the same hole with the guard attached |
| **C3** | Guard + conditional edge | `demo-05` | guard passes with data, **stops** without it, and refuses `Deploy …` from the registry |

Plus: `demo-02` (dynamic router), `demo-03` (conversational REPL).

---

## In-Session Steps

### Step 1: C1 — study and run the fixed chain (15 min)

```bash
python scripts/week-06/demo-01-fixed-chain.py   # and: node scripts/week-06/demo-01-fixed-chain.js
```

Watch the audit trail: every node records itself (`extract_service → retrieve_context
→ check_build → generate_report`), the report is an `AgentAnswer` (Week 2 contract),
and `steps == 4` — the tests assert exactly that. The path is *recorded*, never
reconstructed from state.

### Step 2: dynamic routing (10 min)

```bash
python scripts/week-06/demo-02-dynamic-routing.py
```

The planner node proposes, the registry disposes. Note what's structural vs prompt:
the router *suggests* `check_incidents` for a health query sometimes — the scope
check (`allowed` steps for the query category) rejects it, the correction loop runs
once, and the guard resolves the fallback. Anti-cascade is a **contract**, not a
hope.

### Step 3: C2 — remove a step, watch it hallucinate (12 min)

```bash
python scripts/week-06/demo-04-missing-step.py
```

`check_build` is gone. `state['build_status']` is `None`. The naive report node
renders `BUILD: {}` and the model completes the report anyway — because it predicts
tokens, it doesn't reason about missing data. Same mechanism as Week 4's tool-error
hallucination. The demo then attaches the guard to the *same* broken graph and shows
the typed blocked answer instead.

### Step 4: C3 — guards and refusal (15 min)

```bash
python scripts/week-06/demo-05-guard-and-refusal.py
```

Three tests: guard passes → report; guard blocks → typed `ready=False` answer
(written by code, zero LLM spend); `Deploy auth-service to production` → refused
before any LLM routing call, message built from the registry.

**Break it:** in `src/agent.py` set `MAX_STEPS = 2`, run a full-assessment query,
watch `budget_guard` stop the run with a typed answer. Set it back to `10`.

**Extend:** add `get_service_owner` to `src/mcp_server.py`, then add one entry to
`NODE_REGISTRY` — the router catalog, the route map, and the guard requirements all
pick it up automatically. Restart the server, run demo-02. One dict, four surfaces.

---

## Acceptance Criteria

- [ ] C1: fixed chain runs end-to-end; audit trail shows 4 recorded steps; report is an `AgentAnswer`
- [ ] C2: you saw the naive report invent build data from empty state (`demo-04`)
- [ ] C3: guard blocks the missing-step graph with a typed answer; passes with data
- [ ] Refusal: `Deploy auth-service to production` is refused, listing only registry entries
- [ ] You can trace steps + cost per run, and explain where the cost comes from
- [ ] You can flip `TOOL_BACKEND=local` and run the same agent without the MCP server
- [ ] You can explain: *in-graph guards see state; Week 7 guardrails see only I/O*

---

## Self-Learning (Before Week 7)

### Part A: fixed vs dynamic, cost
Run 5 queries through `run_fixed_chain` and `run_dynamic_agent`. Compare steps, LLM
calls, total cost. When is fixed better? When is dynamic worth the planning overhead?

### Part B: coherence audit — THREE cases
For each: what was asked → what the agent planned (from `messages`) → what it
actually did → where it went wrong → what state was lost or hallucinated → what
would fix it. Use demo-03's REPL. Include one refusal and one guard-blocked run.

### Part C: orchestrator design
Sketch orchestrator + sub-agent for "PR review → check affected services →
deployment risk report". Which parts are nodes, which are tools, where does a
human approve?

### Part D: deep question
> You built guards *inside* the agent graph (Week 6). Week 7 adds `src/guardrails.py`
> wrapped *around* the agent. What's the difference? When would you use each?

(Hint: in-graph guards read full typed state — business logic. External guardrails
see only input/output — security, cost, policy. Same word, different surface.)

### ADR exercise (Runbook contribution)
Write a 1-paragraph ADR: *"We route retrieval through the MCP server / keep it as a
local import, because…"* — defend the process-boundary decision. The code supports
both (`TOOL_BACKEND`); the tradeoff is yours to state.

---

## Scope: languages

- **Python** — reference implementation (typed state, seam, three guards, all demos).
- **Node.js** — runs the same demo flow (`scripts/week-06/`) against its own server
  with the original string-typed agent; structural parity with the Python design is
  tracked, not claimed.
- **Java** — port stops at Week 5 (see `java/README.md`). Week 6 is not ported.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ToolFailure: get_build_status …` | MCP server down → `python src/mcp_server.py` (port 8000) |
| Qdrant connection refused | `docker-compose up -d` |
| Retrieval empty / "No index found" | `python -c "from src.rag import index_documents; index_documents()"` (retrieve also lazy-connects to an existing collection) |
| Integration tests skipped | That's the skipif markers working — start Qdrant + MCP server and re-run |
| Node MCP connection refused | Node server is port **3001** (`node src/mcp_server.js`) |
| Guard blocks a query you think should run | Check `REQUIREMENTS[classify_query(query)]` — the guard only demands what the category requires |
| Router proposes a weird step | Watch `messages` — `plan` records proposal, decision, and reason; the registry check is auditable |
| Empty model completions | The loops retry once with a nudge (`_final_answer`); if it persists, provider-side issue |

---

## Runbook Contribution

Write 1 paragraph: *"Our agent's guards are X because Y"* — cover at least two of
the three guard kinds (budget / structural / business) and one thing you'd add in
Week 7.