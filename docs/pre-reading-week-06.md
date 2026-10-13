# Why Single Prompts Break Under Complexity

> Pre-reading for Week 6. 5 minutes.

---

## The Ceiling

A single prompt works for simple tasks: *"Summarize this PR."* Easy.

But real tasks are multi-step: *"Analyze this PR, check if the affected service is healthy, pull recent deploys, and produce a structured report with severity."*

One prompt can't do 4 steps reliably. The model will skip steps, hallucinate answers for steps it couldn't execute, or produce a shallow answer that misses the complexity.

---

## The Solution: Agentic Workflows

Break the task into steps. The model plans, then executes one step at a time, carrying state between steps.

```
Task → Plan → Step 1 (retrieve) → Step 2 (tool call) → Step 3 (structured output) → Done
```

This is the **orchestrator pattern.** One orchestrator decides what to do next. Sub-agents (or the same model in a loop) execute each step.

### The state graph vocabulary (you'll build one in class)

A state machine — LangGraph's unit — has exactly four parts:

- **State:** a typed dict that holds ALL data across steps. Passed explicitly; nothing is "remembered".
- **Nodes:** functions `state → state`. They read fields, do work, write fields.
- **Edges:** which node runs next (hardcoded in a fixed chain).
- **Conditional edges:** a routing function reads state and picks the next node.

This is why agents ≠ chatbots: chatbots have implicit history; agents have explicit,
printable, *validatable* state. If a field can be empty, a guard can see it.

---

## Two Approaches

| | Fixed Chain | Dynamic Routing |
|---|---|---|
| **How it works** | Steps predefined: A → B → C | Model decides steps at runtime |
| **Predictability** | Deterministic, auditable | Unpredictable, may pick wrong steps |
| **Flexibility** | Brittle: breaks on novel tasks | Adapts to any task |
| **Cost** | Lower (fewer LLM calls) | Higher (planning step + execution) |
| **Use when** | The task structure is known | Tasks vary, need runtime adaptation |

---

## The Coherence Problem

Multi-step agents lose the thread. They forget what they've done. They repeat steps. They pursue irrelevant sub-goals.

**State management is the hardest problem in agentic engineering.**

Context engineering for agents:
- **Truncation:** Keep only the last N turns of conversation
- **Summarisation:** Compress completed steps into a one-paragraph summary
- **Compression:** Prune irrelevant history before the context window overflows

---

## When NOT to Use Agents

- Deterministic pipeline → just write code
- Single prompt works → don't over-engineer
- Human-in-the-loop is faster/cheaper → keep the human
- Cost matters more than flexibility → fixed chain

---

## One Question to Hold

Any multi-step workflow your team runs manually — incident response, deployment verification, PR review pipelines — has an agent-shaped hole in it. Which one would you automate first, and where would the human stay in the loop?

---

## Pre-read links (before the session)

| Resource | Why |
|----------|-----|
| [Building Effective Agents (Anthropic)](https://www.anthropic.com/engineering/building-effective-agents) | when a workflow needs an agent at all — and when it doesn't |
| [LangGraph Quickstart](https://langchain-ai.github.io/langgraph/tutorials/introduction/) | the state graph API you'll use in class |
| [LangGraph — Conditional Edges](https://langchain-ai.github.io/langgraph/how-tos/branching/) | routing: the mechanism behind C3's guard |
| [Lilian Weng — LLM Agents](https://lilianweng.github.io/posts/2023-06-23-agent/) | the planning-loop mental model, from first principles |
