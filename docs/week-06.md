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
```

Verify you're ready:

```bash
python -m pytest tests/ -v -k "not analyze_pr and not run_tool_loop"
```

---

## What You Have

Open `src/agent.py`. It's a stub. By the end of this session, it will compose everything from Weeks 2–5:

```
agent.py
├── from src.llm import get_llm          # Week 1
├── from src.schemas import ...          # Week 2 (ServiceReadinessReport)
├── from src.rag import retrieve         # Week 3 (RAG)
├── from src.tools import ...            # Week 4 (tools)
└── LangGraph StateGraph                 # orchestrator
```

**The import graph is now complete.** Every module built so far feeds into the agent.

## Files You'll Touch
- `src/agent.py` — the orchestrator (imports llm, schemas, rag, tools)
- `scripts/week-06/` — demo scripts

---

## In-Session Steps

The moderator runs a demo first (fixed chain: RAG → tool → structured output). Watch, then follow these steps.

> ⚠️ This is the most complex hands-on so far. Pair up if stuck. The agent WILL break — that's the point.

---

### Step 1: Build a fixed chain (15 min)

`src/agent.py` is a stub. Build a 3-step chain using LangGraph:

```python
# src/agent.py
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from src.llm import get_llm
from src.rag import retrieve
from src.tools import get_build_status

class AgentState(TypedDict):
    query: str
    context: str
    build_status: str
    report: str
    steps: int

def retrieve_context(state: AgentState) -> AgentState:
    """Step 1: Retrieve relevant docs from RAG."""
    chunks = retrieve(state["query"], k=3)
    state["context"] = "\n\n".join(chunks)
    state["steps"] += 1
    return state

def check_build(state: AgentState) -> AgentState:
    """Step 2: Call get_build_status tool."""
    result = get_build_status.invoke({"service_name": "payment-api"})
    state["build_status"] = result
    state["steps"] += 1
    return state

def generate_report(state: AgentState) -> AgentState:
    """Step 3: Produce a structured readiness report."""
    llm = get_llm(temperature=0)
    response = llm.invoke([
        SystemMessage(content="You are a DevOps analyst. Produce a readiness report."),
        HumanMessage(content=(
            f"Query: {state['query']}\n\n"
            f"Relevant docs:\n{state['context']}\n\n"
            f"Build status: {state['build_status']}\n\n"
            f"Generate a readiness report with: summary, readiness (ready/blocked), "
            f"and recommended actions."
        )),
    ])
    state["report"] = response.content
    state["steps"] += 1
    return state

# Build the graph
graph = StateGraph(AgentState)
graph.add_node("retrieve", retrieve_context)
graph.add_node("check_build", check_build)
graph.add_node("report", generate_report)
graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "check_build")
graph.add_edge("check_build", "report")
graph.add_edge("report", END)
agent = graph.compile()

# Run it
result = agent.invoke({"query": "Is the payment-api ready for v2.1?", "context": "", "build_status": "", "report": "", "steps": 0})
print(result["report"])
```

**You just built an agent.** 3 steps, state carried between them, runs end-to-end. Confirm: does the report reference the retrieved docs AND the build status?

---

### Step 2: Break the chain (10 min)

The fixed chain always calls `get_build_status("payment-api")`. What if the query is about `auth-service`? Or `inventory-service`?

```python
# Run a different query — agent still checks payment-api
result = agent.invoke({"query": "Is the auth-service ready for release?", ...})
```

The agent ignores the query and checks payment-api. **The chain is hardcoded. It can't adapt.**

Now remove a step. Delete the `check_build` node from the graph. Run a query that needs build status. What happens? The agent skips it silently and produces a report without build data. **Fixed chains are brittle.**

---

### Step 3: Dynamic routing (10 min)

Replace the fixed edges with a router that lets the model decide:

```python
def router(state: AgentState) -> str:
    """Model decides which step to run next."""
    llm = get_llm(temperature=0)
    response = llm.invoke([
        SystemMessage(content=(
            "You are a workflow router. Based on the query and what's been done so far, "
            "decide the next step. Respond with ONLY one word:\n"
            "- 'retrieve' if context is needed\n"
            "- 'check_build' if build status is needed\n"
            "- 'report' if ready to generate the final report\n"
            "- 'done' if the workflow is complete\n\n"
            f"Query: {state['query']}\n"
            f"Steps completed: {state['steps']}\n"
            f"Context available: {'yes' if state['context'] else 'no'}\n"
            f"Build status available: {'yes' if state['build_status'] else 'no'}"
        )),
    ])
    return response.content.strip()

# Replace fixed edges with conditional routing
graph.add_conditional_edges("retrieve", router, {
    "check_build": "check_build",
    "report": "report",
    "done": END,
})
graph.add_conditional_edges("check_build", router, {
    "retrieve": "retrieve",
    "report": "report",
    "done": END,
})
```

Run 3 different queries. Does the model route differently? **Cost:** compare calls — fixed chain = 3 LLM calls. Dynamic = 3 + 1 per routing decision.

---

### Step 4: Add a guard (5 min)

Prevent runaway agents:

```python
def guard(state: AgentState) -> str:
    """Stop if too many steps or cost too high."""
    if state["steps"] >= 10:
        return "done"
    return router(state)  # delegate to normal routing

# Replace router with guarded version
graph.add_conditional_edges("retrieve", guard, {...})
graph.add_conditional_edges("check_build", guard, {...})
```

Run a query that would loop. The guard stops it at 10 steps. In production: cost guard (`if cost > $2.00`), not just step count.

---

### Step 5: Explore (remaining time)

```bash
# Study the agent implementation
cat src/agent.py

# Run the full demo
python scripts/week-06/demo-01-fixed-chain.py
python scripts/week-06/demo-02-dynamic-routing.py
```

---

## Acceptance Criteria
- [ ] Fixed 3-step chain (retrieve → tool → report) runs end-to-end
- [ ] A query about a different service exposes the hardcoded limitation
- [ ] Dynamic routing adapts to 3 different queries with different step sequences
- [ ] Guard stops the agent at 10 steps or $2.00
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
| Agent loops infinitely | Add the guard — step limit or cost limit |
| Router always picks the same step | Improve the routing prompt. Make decision criteria explicit. |
| State not carrying between steps | Check that each node returns the state dict |

---

## Runbook Contribution

Write a 1-paragraph ADR: "We chose [fixed-chain / dynamic-routing] for our agent because…"
