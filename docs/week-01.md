# Week 1 — AI-First Engineering: Why, What, How

**Session type:** Kick-off. No code to write. You've already run `verification.py` — you're ready.

---

## What We'll Cover

- **The gap:** "AI bolted on" vs "AI-first by default." Why this matters for how we build software.
- **The contrast:** AI Engineering vs Traditional Engineering — what transfers, what's new.
- **The architecture:** Walk through the full DevBuddy diagram. See where each week fits.
- **The series:** Cadence, moderator model, rubric (Levels 0–3), capstone.
- **What we need from you:** Appetite poll, moderator sign-ups, language shepherds.

---

## Tools You'll Use

| Tool | What it is | When |
|------|-----------|------|
| **OpenRouter** | One API key, any LLM. Cost tracking in headers. | All weeks |
| **LangChain + LangGraph** | Framework for LLM calls, structured output, RAG, tools, agents. | Weeks 2–7 |
| **Qdrant** | Vector database for RAG. Runs via Docker. | Weeks 3–7 |
| **MCP SDK** | Standard protocol for sharing tools across teams. | Week 5+ |
| **Pydantic** | Typed, validated data models. The contract between LLM and your code. | Weeks 2–7 |
| **Pytest** | Standard Python test runner. | All weeks |
| **Promptfoo** | LLM eval framework. YAML configs, multi-model, CI-friendly. [README](../shared/evals/README.md) | Week 2+ |

Promptfoo is how we **test LLM output quality.** You can't `assert result == expected` — the model is non-deterministic. Promptfoo lets you assert properties: "contains X," "is valid JSON," "does NOT hallucinate." Each week has an eval config in `shared/evals/`.

---

## Pre-Reading

You received a 1-page primer: "AI Engineering vs Traditional Engineering." If you haven't read it, do it now — it's 5 minutes and frames the entire series.

---

## Your Commitment

After the session, add your answer to `runbook/commitments.md`:

> *"I want DevBuddy to help me with _____"*

This is your personal stake. It's what you're building toward.

---

## Pre-Assessment

We'll do a 10-question diagnostic during the session. Anonymous. Same questions at the end of Week 7 — we measure the shift in architectural judgment, not technical vocabulary.

---

## What's Next

Week 2: **Structured Outputs.** You'll make the LLM return typed, validated JSON — not prose your pipeline can't parse. This is the foundation everything else builds on.
