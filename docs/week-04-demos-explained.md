# Week 4 Demos — What Each One Does, Shows, and Teaches

A walkthrough of the six Python RAG→tools demo scripts in
`python/scripts/week-04/` (demo-00 … demo-05). Each section covers:
**what the script does**, **what you actually see**, **why the behaviour
is that way**, and **the learning you should take away**.

> **The message of the week** (the thread from Week 3):
> *Week 3 gave the model a memory — you boxed its input (retrieval).
> Week 4 gives it hands — you box its actions (tools).*
> **The model proposes. Your code disposes.** The model never runs your
> code: it returns a request `{name, args}`, and your application decides
> whether that request becomes an action. Safety never comes from the
> model — it comes from the boundary you draw.

Numbers quoted below are from typical runs against the shipped
`src/tools.py` with `gpt-4o-mini` via OpenRouter. Routing and wording vary
run to run — the demos print what actually happened, and so should you.

> **Prerequisites:** `OPENROUTER_API_KEY` in `.env` (demos 01–04 need the
> LLM; demo-05 also needs Qdrant running — `docker-compose up -d`). Demo-00
> is print-only and needs nothing. The shared engine is `src/tools.py`
> (3 tools split into raw functions + `@tool` wrappers, `execute_tool_safely`,
> `flaky`, `run_tool_loop[_with_trace]`, `MAX_TOOL_TURNS=6`).

---

## The six demos at a glance

| Demo | Concept | The one-line lesson |
|------|---------|---------------------|
| 00 — Tradeoffs | When tool calling is worth it (and when it isn't) | Deterministic paths don't need an LLM in the loop |
| 01 — Tool Call | Wire one tool, walk the loop by hand | The model could not have run it — it returned a request |
| 02 — Routing | Model picks between tools | Routing is a design problem: **your descriptions** taught it |
| 03 — Failure | Retry + denial in the app layer | Retry and safety are CODE decisions, not prompt text |
| 04 — Full trace | Audit log + cost | If you can't trace it, don't ship it — and it has a bill |
| 05 — RAG bridge | Retrieval as a tool | A tool is just data with a name |

---

## Demo 0 — Tradeoffs & When NOT to Use Tool Calling

Run: `python scripts/week-04/demo-00-tradeoffs.py`  *(instant — no LLM, no network)*

### What it does
Prints the framing: the boundary, the loop, the pros, the cons, the
"when NOT to use" list, and where each control lives.

### What you see
- The boundary: *model returns a request; your code decides whether it becomes an action.*
- **Pros** — live data, grounded decisions, extensibility, auditability.
- **Cons** — latency (each round = a full LLM call), token cost that compounds as results re-enter context, a new failure surface, misrouting, an injection surface.
- **When NOT to use it** — deterministic pipelines, always-the-same-single-call flows, sub-100 ms critical paths.

### Why
Tool calling is an architecture, not a feature. Its value is delegation with a *boundary*; its cost is a new failure and billing surface per capability. The judgment call is which side dominates for a given flow.

### The learning
A senior leaves able to say *"when NOT to use tools"* out loud — and to justify it. The rest of the demos are that claim in action.

---

## Demo 1 — Tool Call: Wire a tool, watch the model call it

Run: `python scripts/week-04/demo-01-tool-call.py`

### What it does
Binds the real `get_build_status` from `src.tools`, asks *"Is the payment-api healthy?"*, then walks the loop by hand: see the request → execute it yourself via `execute_tool_safely` → inject the result → get the answer. If the model answers without calling a tool, it says so instead of crashing.

### What you see
```
Model decided to call: get_build_status
With arguments:         {'service_name': 'payment-api'}
Tool returned: {"status": "degraded", "last_deploy": "2026-06-28T06:45:00Z", ...}
Model: The payment-api service is currently in a degraded state. …
```

### Why
`bind_tools` gives the model a *schema*, not a function. The model's entire output is a JSON request; nothing runs until `execute_tool_safely` decides to. The separation is structural, not stylistic.

### The learning
The demo's title is the point: **the model could NOT have run it.** It proposed; your code disposed. No tool call was ever "executed by the LLM".

---

## Demo 2 — Routing: two tools, one question

Run: `python scripts/week-04/demo-02-tool-routing.py`

### What it does
**Part A** asks four questions against the real tools and prints the *observed* calls. **Part B** asks one question against two bindings of the same tools — VAGUE descriptions vs PRECISE descriptions — to expose the routing lever.

### What you see (one typical run)
```
User: Is the auth-service healthy?            → get_build_status(auth-service)
User: Last 2 deployments for payment-api?      → get_recent_deploys(payment-api, limit=2)
User: Active incidents for inventory-service?  → get_active_incidents(inventory-service)
User: What's the latest build status?          → NO tool called (no service named)
Part B (same question):
  VAGUE    descriptions → get_build_status + get_recent_deploys
  PRECISE descriptions → get_build_status + get_recent_deploys
```
Part B's two rows can differ run to run — when they match, that's data too.

### Why
Routing is driven by the tools' **names and descriptions** (the schema), not by magic. An ambiguous query with no service name regularly defeats routing — the model has nothing to anchor on. Vague descriptions blur the boundary between tools; precise ones tell the model *when* each applies.

### The learning
**Routing is a design problem, not a model problem.** When routing is wrong, the fix is usually in the tool description, the tool count, or the query — not a "smarter model". And since routing varies, *observe it; never assert it*. (The same cases are scored automatically in `shared/evals/week-04-tool-selection.yaml`.)

---

## Demo 3 — Failure: retry & denial live in the app layer

Run: `python scripts/week-04/demo-03-tool-failure.py`

### What it does
**Act 1** drives one tool call through `execute_tool_safely` three times, wrapping the *raw* `build_status` with `flaky(fail_first_n=N)` — deterministic, no global counters. **Act 2** asks the registry for a tool that doesn't exist. **Act 3** feeds a structured error to the model and watches it degrade gracefully.

### What you see
```
scenario: normal     → ✅ returned: {"status": "degraded", ...}
scenario: transient  → ⚠️ attempt 1 failed (Simulated failure 1/1) — retrying…
                       ✅ returned: …
scenario: exhausted  → ⚠️ attempt 1 failed … ⚠️ attempt 2 failed …
                       ❌ structured error after 3 attempts
Request: delete_production_db({}) → {"error": "Unknown tool: …",
                                      "available_tools": ["get_build_status", …]}
Model's answer (given the error): "The tool is temporarily unavailable…
  the status of payment-api remains unknown at this time."
```

### Why
The retry loop, the sleep, the structured-error shape, and the whitelist all live in `execute_tool_safely` — deterministic, testable code. The model never sees the retries; it only ever sees a final success or a structured error. `flaky` keeps the failure injection deterministic and per-instance, so the demo doesn't depend on call order or chance.

### The learning
**Retry, denial, and fallback are code decisions — the prompt is the wrong place for safety.** A model's "recovery" is unreliable by design; the app layer is what ships. Never trust the raw tool request: route everything through the registry, which denies tools the model was never given.

---

## Demo 4 — Full tool loop: trace, audit, and the bill

Run: `python scripts/week-04/demo-04-full-trace.py`

### What it does
Runs three questions through `run_tool_loop_with_trace` and prints each step with its **token cost**, plus per-query and run totals.

### What you see (one typical run)
```
QUERY: Is the auth-service healthy?
  [DECIDE]   in= 530 out=  57   …         (calls get_build_status)
  [EXECUTE]  get_build_status
  [DECIDE]   in= 599 out=  71   …         (chained: calls get_active_incidents)
  [EXECUTE]  get_active_incidents
  [DECIDE]   in= 638 out=  92   …
  [ANSWER]   in= 638 out=  92
  → 4 LLM calls; 2,405 in / 312 out / 2,717 total tokens
… (3 queries)
This run: 10 LLM calls, 8,462 total tokens.
```

### Why
Each `decide` is a separate LLM round-trip; tool results re-enter the context, so tokens grow per round. The trace makes the *audit trail* and the *cost* the same artifact. `MAX_TOOL_TURNS=6` caps the loop because a model that never stops calling tools is a cost event, not a feature.

### The learning
**If you cannot trace a decision — replay who decided, what executed, what it returned, what it cost — you should not ship it.** The trace is the audit log; the token counter is the bill. This is the "cons" of demo-00 made visible.

---

## Demo 5 — RAG as a tool: a tool is just data with a name

Run: `python scripts/week-04/demo-05-rag-bridge.py`  *(needs Qdrant)*

### What it does
Defines `get_build_status_from_docs(service_name)` whose data source is **Week 3's vector store**: it calls `src.rag.retrieve()` and asks the LLM to extract a status JSON from the chunks. Runs it through the same `execute_tool_safely` app layer as every other tool.

### What you see
```
Compare with src.tools.get_build_status — SAME interface, different data source.
Tool returned: {"status": "healthy", "last_deploy": "2026-06-27"}
```
Notice: the hardcoded dict says payment-api is **degraded**; the docs say **healthy**. Same tool contract, different source, different truth.

### Why
The tool is a contract — name + args + JSON out. Where the data comes from (dict, API, vector store) is an implementation detail. Nothing in the orchestrator changes.

### The learning
**Composition.** Week 6's agent won't care whether a tool reads a dict, an API, or RAG — tools are interchangeable data providers behind a stable interface.

---

## The senior take-home (say this out loud)

- **Routing** (which tool / what args) — the model decides, but *my descriptions trained it*. Routing is a design problem.
- **Execution** (whether it actually runs) — *my whitelist* decides, not the model.
- **Failure** (retry / denial / fallback) — *code decisions*: deterministic, testable, auditable. The prompt is the wrong place for safety.
- **Cost & audit** (what it did, what it cost) — *my trace* and a bounded loop. If I can't trace a decision, I don't ship it.
- **When not to use it** — deterministic pipelines and single-call flows are just code.

## How to read the output

- `→ get_build_status({'service_name': …})` — the model's **request**. Nothing has run yet.
- `[DECIDE]` / `[EXECUTE]` / `[ANSWER]` — the trace steps; `[DECIDE]` and `[ANSWER]` each cost an LLM call (tokens shown).
- `structured error` with `attempts: N` — the app layer gave up after N tries and told the model exactly that.
- `available_tools: […]` — the registry's answer to a tool the model was never given: a denial, not an execution.

## Interactive elements

- **`PAUSE & PREDICT`** — guess before the reveal (e.g. "which tool will it pick?", "how many LLM calls?"). Prediction-then-reveal is what turns reading into learning.
- **`YOUR TURN`** — concrete follow-ups: overlap a third tool, run routing 5×, price a chained answer at 1,000 users, gate weak retrieval with `min_score`.
- **Observed-not-asserted** — no demo claims the model "will" do anything; they print what it did.

## Cross-language note

Python and Node.js are now in sync for week-04: identical demo set (00 → 05), identical `src/tools` engine (raw functions + wrappers, `flaky`, bounded multi-round loops with per-step token capture, registry-guarded `executeToolSafely`). Java parity is not yet in scope for this branch.
