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

The executable validation table (needs the services above, ~1 min):

```bash
cd shared/evals
npx promptfoo@latest eval --config week-06-agent-planning.yaml
# → 3 passed: full pipeline · health-only (no cascade) · deploy refusal
```

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
| **C1** | Fixed chain | `demo-01` | the **compiled graph** drives the transitions (streamed, not a for-loop); after every node: its audit event + per-step cost, which state fields are **filled**, which are still empty |
| **C2** | Missing-step hallucination | `demo-04` | node removed → naive report renders `BUILD: {}`. Detection is structural: fabricated `source="tool"` evidence, or affirmative build claims vs state (honest hedges are reported as hedges) — then the same hole with the guard attached |
| **C3** | Guard + conditional edge | `demo-05` | four tests: guard passes → report · guard blocks (typed answer, **cost-proven zero report spend**) · `Deploy …` refused from the registry · budget stop at `MAX_STEPS=2` |

Plus: `demo-02` (dynamic planner — prints every *proposed → corrected → dispatched*
decision and a measured fixed-vs-dynamic cost), `demo-03` (conversational REPL).

---

## In-Session Steps

### Step 1: C1 — study and run the fixed chain (15 min)

```bash
python scripts/week-06/demo-01-fixed-chain.py   # (node demo-01 is a lighter run: same graph, less tracing)
```

The demo **streams the compiled graph** — `build_fixed_chain()` turns nodes +
hardcoded edges into a runtime, and the runtime walks them (`extract → retrieve →
check_build → report → END`). Nothing below is a hand-written loop. After each
transition you get:

- the node's audit event with its **cost delta** (every event carries one),
- which state fields are now **filled**, which are **still `None`** —
  an empty field here is exactly the C2 fuel demo-04 will burn,
- the final `AgentAnswer` (Week 2 contract) and `steps == 4` — the tests assert it.

### Step 2: dynamic routing (10 min)

```bash
python scripts/week-06/demo-02-dynamic-routing.py
```

The planner node proposes, the registry disposes — and the demo **prints every
decision**:

```
🧠  plan decisions (LLM proposes → code disposes):
   ✅ proposed check_build → accept  · $0.000053
   ⚠️  proposed check_build → corrected  → dispatched: retrieve  · $0.000112
   ⚠️  proposed check_build → fallback  → dispatched: report     · $0.000114
```

What's structural vs prompt: the router *suggests* an already-collected or
out-of-scope step, the scope check rejects it, the correction loop runs once, and
the guard resolves the fallback. Anti-cascade is a **contract**, not a hope. The
demo also runs the same query through demo-01's fixed chain and prints both costs —
measured, not asserted.

### Step 3: C2 — remove a step, watch it hallucinate (12 min)

```bash
python scripts/week-06/demo-04-missing-step.py
```

`check_build` is gone. `state['build_status']` is `None`. The naive report node
renders `BUILD: {}` and the model completes the report anyway — because it predicts
tokens, it doesn't reason about missing data. Same mechanism as Week 4's tool-error
hallucination.

Detection checks **claims against state**, not keywords: fabricated evidence
(`source="tool"` citing build data while state is `None`) or an *affirmative* build
claim (status words near "build") — hedges like *"build status was not provided"*
are honest and are **not** flagged (a naive keyword count would false-positive on
"incide**ci**nts" and on hedges that mention "build"). If this run hedges, the demo
says so: *hedging is luck, not a guardrail.*

The demo then attaches the guard to the *same* broken graph and shows the typed
blocked answer instead.

### Step 4: C3 — validity, refusal, budget (15 min)

```bash
python scripts/week-06/demo-05-guard-and-refusal.py
```

Four tests, each printing the guard's actual decision (`validate → PASS/BLOCKED`)
from the audit — never inferred:

1. build checked → guard passes → report generated
2. `check_build` removed → guard blocks with a typed `ready=False` answer, and the
   **cost proof** shows `generate_report` never ran (blocked run ≈ $0.00001 vs
   $0.0004 — *a guard that spends tokens isn't a guard, it's a suggestion*)
3. `Deploy auth-service to production` → refused before any LLM routing call,
   message built from the registry
4. budget guard: `MAX_STEPS` forced to `2` → run stops with the typed
   `AGENT BUDGET EXCEEDED` answer (zero tokens), then restores the constant

**Break it yourself:** in the REPL or a scratch run, set `MAX_STEPS = 4` in
`src/agent.py`, re-run a full-assessment query, watch where it stops. Set it back.

**Extend:** add `get_service_owner` to `src/mcp_server.py`, then add one entry to
`NODE_REGISTRY` — the router catalog, the route map, and the guard requirements all
pick it up automatically. Restart the server, run demo-02. One dict, four surfaces.

---

## Acceptance Criteria

- [ ] C1: the compiled graph drives the fixed chain (streamed); audit shows 4 recorded steps with **per-step cost deltas**; report is an `AgentAnswer`
- [ ] C2: you saw the naive report vs state — detected hallucination, or an honestly labeled hedge (`demo-04`)
- [ ] C3: guard passes with data; blocks the missing-step graph with a typed answer at measurably lower cost; budget stops at `MAX_STEPS=2`
- [ ] Refusal: `Deploy auth-service to production` is refused, listing only registry entries, with the plan reason in the audit
- [ ] You can read a plan record (`proposal → decision → dispatched`) and explain every correction
- [ ] You can flip `TOOL_BACKEND=local` and run the same agent without the MCP server
- [ ] You can explain: *in-graph guards see state; Week 7 guardrails see only I/O*

---

## Self-Learning (Before Week 7)

### Part A: fixed vs dynamic, cost
demo-02 already measures one query — start from that. Run 5 queries through
`run_fixed_chain` and `run_dynamic_agent`. Compare steps, LLM calls, total cost
(every audit event carries its delta). When is fixed better? When is dynamic worth
the planning overhead?

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
| Empty model completions | The loops retry once with an nudge (`_final_answer`); if it persists, provider-side issue |
| `demo-04` prints "the model hedged this run" | That's an honest outcome — the model declined to assert build data. The vulnerability is still shown; hedging is luck, not a guardrail |
| Retrieval returns empty strings in one language | Node and Python use SEPARATE Qdrant collections (`devbuddy-docs-node` / `devbuddy-docs`) — payload schemas are incompatible; re-index the language you're using |

---

## Runbook Contribution

Write 1 paragraph: *"Our agent's guards are X because Y"* — cover at least two of
the three guard kinds (budget / structural / business) and one thing you'd add in
Week 7.