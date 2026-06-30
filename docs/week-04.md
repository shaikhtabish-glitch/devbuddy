# Week 4 — Tool Use

**Goal:** Give DevBuddy real functions it can call. The model decides *when* to call them. Your code executes and enforces.

---

## Setup

```bash
cd python
source .venv/bin/activate
git pull upstream main
pip install -r requirements.txt

# Qdrant must be running (Week 3+)
docker-compose up -d   # or 'docker compose up -d'
curl http://localhost:6333/healthz
```

Verify you're ready:

```bash
# Week 2 + 3 baseline
python -m pytest tests/test_schemas.py -v -k "not analyze_pr"
python -m pytest tests/test_rag.py -v
```

---

## What You Have

Open `src/tools.py`. It's a stub. By the end of this session, it will contain:

- **Tool definitions** — real functions the model can call via LangChain's `@tool` decorator
- **Tool implementations** — mock data sources (build status, deployment history) that simulate live APIs
- **A tool-calling loop** — the `decide → execute → return` pattern
- **Error handling** — tool failures caught in your application layer, not the prompt

## The Architectural Boundary

```
MODEL (decision layer)              YOUR CODE (execution layer)
     │                                    │
     │ "I need build status for            │
     │  payment-api"                       │
     │───────────────────────────────────→│
     │                                    │ get_build_status("payment-api")
     │                                    │ → {status: "degraded"}
     │          result injected           │
     │←───────────────────────────────────│
     │ "Payment API is degraded."         │
```

**The model never runs your code.** It asks. You execute. This is the single most important principle in AI-first systems.

## Files You'll Touch
- `src/tools.py` — your implementation (imports `src.llm`)
- `src/llm.py` — already built (`get_llm()` factory)
- `scripts/week-04/` — demo scripts and hands-on exercises

## Mock Data (reusing from earlier weeks)
- `shared/data/deploy-log.md` — 4 real deployments with statuses (Week 3)
- `shared/data/incident-log.md` — 3 incidents with error codes (Week 3)
- `shared/data/service-readiness-*.json` — structured mock data (Week 2)

---

## In-Session Steps

The moderator runs two demos first (tool call + trace the loop, then tool failure). Watch them, then follow these steps.

---

### Step 1: Wire your first tool (10 min)

Define `get_build_status(service_name)` as a LangChain tool and call it:

```python
from langchain_core.tools import tool
from src.llm import get_llm
from langchain_core.messages import HumanMessage

# 1. Define the tool
@tool
def get_build_status(service_name: str) -> str:
    """Return the current build status for a given service."""
    # Mock data — in production this hits a real API
    statuses = {
        "auth-service": "healthy",
        "payment-api": "degraded",
        "inventory-service": "unknown",
    }
    return statuses.get(service_name, f"unknown — no data for '{service_name}'")

# 2. Bind it to the LLM
llm = get_llm(temperature=0)
llm_with_tools = llm.bind_tools([get_build_status])

# 3. Ask a question that needs the tool
response = llm_with_tools.invoke([
    HumanMessage(content="Is the payment-api healthy?")
])

print(response.tool_calls)
# → [{'name': 'get_build_status', 'args': {'service_name': 'payment-api'}, ...}]
```

The model didn't run `get_build_status`. It returned a tool call. **Your code** must execute it.

---

### Step 2: Execute the tool and complete the loop (10 min)

The model decided. Now you execute:

```python
import json

# Execute the tool call
tool_call = response.tool_calls[0]
result = get_build_status.invoke(tool_call["args"])

# Inject the result back into the conversation
from langchain_core.messages import ToolMessage

messages = [
    HumanMessage(content="Is the payment-api healthy?"),
    response,  # the model's tool call request
    ToolMessage(content=result, tool_call_id=tool_call["id"]),
]

# Ask the model to produce a final answer
final = llm_with_tools.invoke(messages)
print(final.content)
# → "The payment-api is currently degraded."
```

The loop: **Request → Decide → Execute → Return → Answer.** Commit it to memory.

---

### Step 3: Add a second tool (10 min)

Now the model must choose between tools:

```python
@tool
def get_recent_deploys(service_name: str, limit: int = 5) -> str:
    """Return the last N deployments for a service."""
    deploys = {
        "auth-service": [
            {"sha": "abc123", "status": "success", "timestamp": "2026-06-28T08:15:00Z"},
            {"sha": "789ghi", "status": "success", "timestamp": "2026-06-27T14:30:00Z"},
        ],
        "payment-api": [
            {"sha": "def789", "status": "success", "timestamp": "2026-06-28T06:45:00Z"},
            {"sha": "jkl345", "status": "rolling_back", "timestamp": "2026-06-27T22:00:00Z"},
            {"sha": "pqr901", "status": "failed", "timestamp": "2026-06-27T20:15:00Z"},
        ],
    }
    service_deploys = deploys.get(service_name, [])
    return json.dumps(service_deploys[:limit], indent=2)

llm_with_tools = llm.bind_tools([get_build_status, get_recent_deploys])

response = llm_with_tools.invoke([
    HumanMessage(content="What was deployed recently and is everything healthy?")
])

for tc in response.tool_calls:
    print(f"Model wants to call: {tc['name']}({tc['args']})")
```

Some engineers will see the model call both tools. Some will see it call just one and guess the rest. **Tool descriptions determine routing quality.**

---

### Step 4: Break a tool — handle failure (10 min)

Make a tool throw an exception. Handle it in your application layer:

```python
@tool
def get_build_status(service_name: str) -> str:
    """Return the current build status for a given service."""
    import random
    if random.random() < 0.3:  # 30% failure rate
        raise ConnectionError(f"Could not reach monitoring API for '{service_name}'")
    statuses = {"auth-service": "healthy", "payment-api": "degraded"}
    return statuses.get(service_name, "unknown")


def execute_tool_safely(tool_call, tools_map):
    """Execute a tool call with error handling in the application layer."""
    tool_name = tool_call["name"]
    try:
        tool_fn = tools_map[tool_name]
        return tool_fn.invoke(tool_call["args"])
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "tool": tool_name,
            "status": "failed",
            "hint": "The tool is temporarily unavailable. Try again or use cached data."
        })
```

The model sees the structured error and can decide: retry, try a different tool, or tell the user. But **your code controls** whether to actually retry — not the model.

---

### Step 5: Explore (remaining time)

```bash
# Study the full tool-calling loop
cat scripts/week-04/demo-01-tool-call.py

# Play with tool routing
cat scripts/week-04/demo-02-tool-routing.py

# Break things and observe recovery
cat scripts/week-04/demo-03-tool-failure.py

# Full trace with all 3 tools — see every step
python scripts/week-04/demo-04-full-trace.py
```

---

### Bonus: Connect tools to your Week 3 RAG index (5 min)

Your tools use hardcoded mock data — great for learning. But you already built
a RAG pipeline in Week 3 with real documents. Let's connect them:

```python
from src.rag import retrieve
from src.llm import get_llm
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
import json

@tool
def get_build_status_from_docs(service_name: str) -> str:
    """Return the build/health status for a service by searching our docs."""
    chunks = retrieve(f"{service_name} build status health deploy", k=5)
    context = "\n\n".join(chunks)

    llm = get_llm(temperature=0)
    response = llm.invoke([
        SystemMessage(content=(
            "Extract the build/health status from the context. "
            "Return JSON with 'status' (healthy/degraded/down/unknown) "
            "and 'last_deploy' (timestamp). Only use data from the context."
        )),
        HumanMessage(content=f"Service: {service_name}\n\nContext:\n{context}")
    ])
    return response.content
```

**What changed?** The tool interface is identical — same name pattern, same args,
same return shape. But the data source went from a hardcoded dict to your Week 3
vector store. This is the compositional pattern: `tools.py` doesn't need to import
`rag.py`. The tool just needs data. Where that data comes from is an implementation
detail.

In Week 6, the agent will compose both modules directly — orchestrating retrieval
and tool calls as separate steps. This bonus is just a preview of that pattern.

---

## Acceptance Criteria
- [ ] `get_build_status` is defined as a LangChain `@tool` and the model calls it with correct arguments
- [ ] The full decide → execute → return loop runs end-to-end
- [ ] When given two tools, the model picks the right one for a question that clearly needs one
- [ ] Tool failure is caught in the application layer and a structured error is returned to the model
- [ ] You can explain: *"The model decides. My code executes. That boundary is everything."*

---

## Self-Learning (Before Week 5)

> **The take-home is error handling architecture.** Tool calling is easy. Surviving failure is engineering.
>
> Reference: `src/tools.py` has the full implementation — 3 tools, `execute_tool_safely()`, and the complete loop. Use it as a guide, but write your own from scratch.
>
> Docs: [LangChain Tools](https://docs.langchain.com/oss/python/langchain/tools) — `@tool` decorator, `StructuredTool`, `bind_tools()`, and tool error handling.

### Part A: Multi-tool routing
- Write your own 3 tools from scratch: `get_build_status`, `get_recent_deploys`, `get_active_incidents`
- Use your own mock data — different from the pre-built version
- Write 5 questions that require different combinations of tools (single tool, two tools, all three, none)
- Document: which questions routed correctly? Which routed wrong? Why?

### Part B: Failure resilience
- Add artificial latency (`time.sleep(1-3)`) and intermittent failures (30% error rate) to one tool
- Build `execute_tool_safely()` with retry logic (max 2 attempts), fallback to cached data, and structured error responses
- Run 10 queries. Document: how many succeeded on first try? How many needed a retry? How many exhausted retries? How did the model respond to each?

### Part C: The boundary diagram
- Draw an architecture diagram showing where each concern lives:
  - Tool definitions → in your code
  - Tool selection → model decides
  - Tool execution → your code
  - Error handling → your code (retry, fallback, circuit breaker)
  - Audit logging → your code
  - Final answer → model
- Add a human-in-the-loop step: where does a human review or approve before the tool executes? What triggers it?

### Part D: Real API design
- Identify one real API your team owns (build status, deployment history, on-call schedule, incident data)
- Sketch the `@tool` definition: name, description, parameters, return type, possible errors
- You don't need to implement it. Just the design. Share it in the channel — others can use it as inspiration for their own tools.

---

## Runbook Contribution

Write a 1-paragraph ADR: "We placed error-handling logic in the application layer, not the prompt, because…"

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Model doesn't call the tool | Check tool name matches the prompt. Add a more descriptive docstring. |
| `bind_tools` not found | Update langchain: `pip install --upgrade langchain-core` |
| Model calls wrong tool | Improve tool descriptions. Make them specific and distinct. |
| `ToolMessage` not found | Import from `langchain_core.messages` |
