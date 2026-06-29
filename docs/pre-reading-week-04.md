# The Model Never Runs Your Code

> Pre-reading for Week 4. 5 minutes.

---

## The Boundary

This is the single most important architectural principle in AI-first systems:

```
MODEL (decision layer)              YOUR CODE (execution layer)
     │                                    │
     │ "I need build status"              │
     │───────────────────────────────────→│
     │                                    │ runs get_build_status()
     │                                    │ validates arguments
     │                                    │ handles errors, retries
     │          result injected           │
     │←───────────────────────────────────│
     │ "Service is healthy"              │
```

**The model decides what to do. Your code executes and enforces.** The model never touches your runtime. It can't call `rm -rf /` or drop a database. Your code is the gatekeeper.

---

## The Loop

Every tool interaction follows the same 5-step pattern:

```
Request → Decide → Execute → Return → Answer
```

1. **Request:** User asks a question ("Is the payment API healthy?")
2. **Decide:** Model analyzes → "I need to call `get_build_status('payment-api')`"
3. **Execute:** Your code runs `get_build_status('payment-api')` → returns `"degraded"`
4. **Return:** Result is injected back into the conversation as a `ToolMessage`
5. **Answer:** Model produces final response: "The payment API is currently degraded."

Commit this to memory. Every AI-first architecture has this loop at its core.

---

## Why This Boundary Matters

| If the model executed code directly | With this boundary |
|---|---|
| Security risk: model could call anything | Your code whitelists available tools |
| No error handling: model's recovery is unreliable | Your code retries, falls back, escalates |
| No audit trail: what was called and why? | Every tool call is logged by your application |
| Prompt injection → model calls dangerous tools | Your code validates arguments before executing |
| Model hallucinates tool results | Your code returns real data |

The model is brilliant at deciding *what* to do. It is terrible at doing it reliably. Let the model decide. Let your code execute.

---

## Tool Descriptions Are Your API Contract

The model routes between tools based on their **names and descriptions**. A vague description → wrong routing:

```python
# Bad — model won't know when to call this
@tool
def check(name: str) -> str:
    """Check something."""
    ...

# Good — model knows exactly what this does
@tool
def get_build_status(service_name: str) -> str:
    """Return the current build status for a given service. 
    Returns 'healthy', 'degraded', 'down', or 'unknown'."""
    ...
```

**Tool descriptions are code.** They go through review. They get versioned. They determine whether your system routes correctly or silently fails.

> **Reference:** [LangChain Tools Documentation](https://docs.langchain.com/oss/python/langchain/tools) — `@tool` decorator, `StructuredTool`, `bind_tools()`, and tool error handling.

---

## When NOT to Use Tool Calling

- The pipeline is deterministic (always call A → B → C) → just write code
- You only ever call one tool → the overhead isn't worth it
- The data is static and fits in a prompt → stuff it, don't call it
- Latency is critical → tool calls add network round-trips

---

## One Question to Hold

Before the session, think of one internal API your team owns that answers a question currently answered by a human. Build status? Deployment history? On-call schedule? Incident data?

That API is a tool waiting to be wired. Today you'll wire your first one.
