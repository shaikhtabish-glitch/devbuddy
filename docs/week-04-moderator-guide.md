# Week 4 — Moderator Guide: The Model Proposes. Your Code Disposes.

> **Time:** 90 minutes. Hard stops at each timebox.
> **The theme:** *Week 3 gave the model a memory — you boxed its input
> (retrieval). Week 4 gives it hands — you box its actions (tools).*
> **Key message:** The model never runs your code. It returns a request
> `{name, args}`; your application decides whether that request becomes an
> action. Safety never comes from the model — it comes from the boundary
> you draw.
> **Blueprint:** `docs/week-04.md` (setup, steps, acceptance criteria).
> **Pre-reading:** `docs/pre-reading-week-04.md`.
> **Demo reference:** `docs/week-04-demos-explained.md`.

---

## The arc you are teaching

| # | Module | Demo | The line engineers take home |
|---|--------|------|------------------------------|
| 0 | Tradeoffs | demo-00 | Tool calling has real costs — deterministic paths don't need it |
| 1 | The boundary | demo-01 | The model could not have run it — it returned a *request* |
| 2 | Routing | demo-02 | Routing is a design problem: **my descriptions** taught it to pick |
| 3 | Failure | demo-03 | Retry, denial, and fallback are **code decisions**, not prompt text |
| 4 | Cost & audit | demo-04 | Every call is a decision I can replay and a bill I can read |
| 5 | Composition | demo-05 | A tool is just data with a name |

**The thread from Week 2 → 4** (seniors respond to this): box the *output*
(schema) → box the *input* (retrieval) → box the *actions* (tools). Same
reflex every week: the framework gives a guarantee; the guarantee isn't the
goal — the boundary *you* own is.

**Senior take-home** — by the end each engineer can say, pointing at each
control, whose job it is:
- *Which tool / what args* → model decides, but my descriptions trained it
- *Whether it actually runs* → my whitelist, not the model
- *Retry / denial / fallback* → code decisions — deterministic, testable, auditable
- *What it cost / did* → my trace and a bounded loop — if I can't trace it, I don't ship it
- *When not to use it* → deterministic pipelines and single-call flows are just code

---

## Pre-Session Checklist (48 hours before)

- [ ] **Qdrant running:** `docker-compose up -d` from repo root →
      `curl http://localhost:6333/healthz` → `healthz check passed`.
      Server is **pinned to v1.17.1** to match the clients — no version warning.
- [ ] **LLM keys, per language:** Python `OPENROUTER_API_KEY` in `python/.env`;
      Node in `nodejs/.env`; Java `openrouter.api.key` + `devbuddy.model` in
      `java/src/main/resources/application.properties`. Demos 01/02/04/05 need
      the LLM; 00 and 03 are deterministic (no key).
- [ ] **Embedding model pre-downloaded** (Python/Node ~80 MB, Java DJL ~24 MB).
      Run demo-05 (or a RagTest) once so the first-run download doesn't eat time.
- [ ] **All six demos rehearsed** in at least one language from a clean state:
      Python `python scripts/week-04/demo-00-*.py` … `demo-05-*.py`;
      Node `node scripts/week-04/demo-00-*.js` …;
      Java `mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week04.Demo0X…`.
- [ ] **Know your numbers** (they vary run to run — that's the point):
      routing is observed, never guaranteed; demo-04 order-of-magnitude is
      ~3 LLM calls / ~1.5–3k tokens per query and ~5–10k tokens for three
      queries; a well-behaved model refuses or chains depending on question.
- [ ] **Model nuance check:** the repo may route to `gpt-4o-mini` or
      `xiaomi/mimo-v2.5` depending on the machine's `.env`. Both hold up — but
      **never promise a fixed routing/refusal outcome**. Print what happened.
- [ ] **Tests verified** per language: Python `pytest tests/test_tools.py
      tests/test_rag.py -q`; Node `npx vitest run tests/test_tools.js`; Java
      `mvn test -Dtest=ToolEngineTest,RagTest`.
- [ ] **Backup:** screen recording of each demo in case of live failure.
- [ ] **Ops team member** in the room as backup.

---

## The Demos You'll Run (all six, each language-parallel)

**Demo 0 — Tradeoffs (`demo-00` · 3 min, no LLM)**
1. Run it. It is instant — framing only.
2. *"Tool calling is an architecture, not a feature. Its value is delegation
   with a boundary; its cost is a new failure + billing surface per
   capability. Keep the 'when NOT to use it' list — you'll use it in the
   debrief."*

**Demo 1 — Wire a tool (`demo-01` · 8 min)**
1. Run "Is the payment-api healthy?". The model emits a request
   `{name, args}`; your code executes it; answer is grounded.
2. *"Notice what the model produced: a JSON *request*, nothing more. It could
   not have run `get_build_status`. YOUR code decided whether that request
   became an action — and you kept the trace."*

**Demo 2 — Routing (`demo-02` · 10 min)**
1. Part A: four questions, observed calls (one has no service name — watch).
2. Part B: same question against VAGUE vs PRECISE descriptions.
3. *"Routing is a design problem, not a model problem. When it misroutes,
   the fix is usually the description, the tool count, or the query — not a
   'smarter model'. Observe it; never assert it."*
4. Point at `shared/evals/week-04-tool-selection.yaml`: *"these exact cases
   are scored automatically."*

**Demo 3 — Failure (`demo-03` · 10 min, deterministic)**
1. Act 1: retry drill — normal → fail-once-retry → exhausted structured error.
2. Act 2: the guardrail — `delete_production_db` is denied by the registry.
3. *"Retry, denial, and error format are CODE decisions — deterministic,
   testable, auditable. The model's recovery is unreliable by design; your
   application layer is what ships. Never trust the raw tool request."*

**Demo 4 — Trace + cost (`demo-04` · 8 min)**
1. Three queries; per-query and run-total tokens printed.
2. *"The trace is the audit log; the token counter is the bill. If you cannot
   trace a decision — who decided, what executed, what it returned, what it
   cost — you should not ship it. The loop is bounded (`MAX_TOOL_TURNS`): a
   model that never stops calling tools is a cost event, not a feature."*
3. Pause and predict the LLM-call count before the multi-tool query.

**Demo 5 — RAG as a tool (`demo-05` · 5 min, needs Qdrant)**
1. The tool calls `retrieve()` from Week 3 + LLM extraction. Run it.
2. *"A tool is just data with a name. The dict says payment-api is degraded;
   the docs say healthy. Same contract, different source — and nothing else
   in the stack changed. That's composition."*

---

## Session Script

### 0:00–12:00 — Framing (12 min)

1. **Open (3 min):** "Last week you controlled what the model *knows* —
   retrieval. This week you control what it can *do* — tools. The model
   proposes; your code disposes. The model never runs your code."
2. **The boundary + loop (4 min):** request → decide → execute → return →
   answer. Draw it. *"Every round-trip is another LLM call = latency +
   tokens."*
3. **Where the control lives (3 min):** routing / whitelist / retry-denial /
   trace / when-not — each is a named control with an owner (the take-home).
4. **Run demo-00 (2 min):** the tradeoffs board.

**Time check at 12:00. Move to the live demos.**

### 12:00–50:00 — Live demos + hands-on (38 min)

**Step 1: demo-01 live (8 min) — YOU.** Wire one tool, trace the request→execution.
*"It returned a request. Your code disposed."*

**Step 2: demo-02 live (10 min) — YOU.** Part A observed routing (predict
first), then Part B the description lever. *"The tool description is code.
It goes through review."*

**Step 3: Everyone wires a tool (12 min) — ENGINEERS.** Blueprint Steps 1–3:
wire `get_build_status`, execute + complete the loop, add a second tool.
Walk around. *Common issues:* tool schema/signature mismatch, model answers
without calling (ask with an explicit service name), Node deps not installed.

**Step 4: demo-03 live (8 min) — YOU.** Retry drill + the denial guardrail.
Then have them run the drill themselves (Blueprint Step 4). *"The prompt is
the wrong place for safety."*

**Time check at 50:00. Move to cost + explore.**

### 50:00–68:00 — Cost, composition, explore (18 min)

**Step 5: demo-04 (8 min).** Predict call-count, watch the token bill.

**Step 6: demo-05 (4 min).** RAG as a tool — composition.

**Step 7: Explore (6 min).** Run the remaining demos in your language; try
the `YOUR TURN` prompts (overlap a third tool; price ×1,000 users; `min_score`
guard in demo-05).

### 68:00–90:00 — Debrief (22 min)

1. **Routing (5 min).** "Who saw a wrong route? What drove it — description,
   tool overlap, or a vague query?" → *descriptions are the lever.*
2. **The boundary (4 min).** "Where does retry live? Denial? The audit log?
   Why is the model the wrong place for any of these?"
3. **Cost & when-not (5 min).** "What did a chained answer cost in tokens?
   At 1,000 users? When would you NOT give the model tools?"
4. **Formatting + errors (4 min).** "How should tool results be formatted for
   the model? What does a good structured error look like?" → JSON in, JSON
   out, truncate, no prose.
5. **Preview Week 5 (4 min).** Agents/orchestration — this tool layer becomes
   what the agent calls. Self-learning Parts A–D due before then.

---

## Common Pitfalls & Recovery

| Situation | Recovery |
|-----------|----------|
| **Qdrant not running / connection refused** | `docker-compose up -d`; `curl localhost:6333/healthz`. Java uses gRPC port 6334. |
| **LLM 401 / no key** | Set the key per language (checklist). Demos 00/03 run without one; narrate 01/02/04/05 from rehearsal. |
| **Model doesn't call the tool** | Tool schema/description issue, or the query is vague. Add an explicit service name; sharpen the description. |
| **Model calls the right tool, wrong args** | Description should state arg meaning; retry with a precise question. |
| **Routing differs from your run** | Expected — routing varies. Say so: "observe, don't assert" is the lesson. |
| **Refusal vs invention varies by model** | Different `.env` models behave differently. Read the answer, classify it, move on. |
| **Node deps missing** | `npm install --legacy-peer-deps` in `nodejs/`. |
| **Java key/model not set** | `application.properties` needs `openrouter.api.key`; demos 01/02/04/05 need it. |
| **Demo-05 slow / no docs** | Index once beforehand (RagTest or demo-05). If Qdrant is down it cannot run — retrieval-only fallback. |
| **Retry drill feels slow** | The 1s backoff is deliberate; run `retryDelayMs`/`maxRetries` explanation, don't skip. |
| **Demo runs over time** | Cut Step 7 explore; never cut the debrief — that's where it solidifies. |

---

## Post-Session Checklist

- [ ] Runbook `week-04.md` updated: routing observations, cost math, ADR seed
- [ ] Channel message: classroom assignment (48 h) + self-learning Parts A–D
      (before Week 5)
- [ ] Encourage the **tool-selection eval** run (`shared/evals/
      week-04-tool-selection.yaml`) to *measure* routing, not trust it
- [ ] Note model-behaviour drift / demo flakiness for ops before the rerun

---

## Language quick-reference

| | Python | Node.js | Java |
|---|--------|---------|------|
| Engine | `src/tools.py` | `src/tools.js` | `devbuddy.tools.*` |
| Retry/deny/flaky | `execute_tool_safely`, `flaky` | `executeToolSafely`, `flaky` | `ToolEngine` |
| Loop + trace | `run_tool_loop[_with_trace]` | `runToolLoop[_WithTrace]` | `ToolLoop` |
| Demos | `scripts/week-04/demo-0*.py` | `scripts/week-04/demo-0*.js` | `devbuddy.scripts.week04.*` |
| Deterministic tests | `tests/test_tools.py` | `tests/test_tools.js` | `ToolEngineTest` |

Same tool names, same JSON contracts, same message — in all three.
