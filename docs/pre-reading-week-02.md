# The Model as a Typed Function

> Pre-reading for Week 2. 5 minutes.

---

## The Problem

You call an LLM. It returns text. You try to parse it with `json.loads()`. It works in dev. In production, the model returns slightly different formatting. Your pipeline breaks. On-call wakes up.

This is **code slop** — free-text responses that downstream code can't reliably consume.

---

## The Solution

Treat the LLM as a **typed function**:

```
input:  { title: "Fix login bug", diff: "changed auth.py line 42" }
output: BuildCheck(project="auth-service", severity="high", summary="...", affected_files=["auth.py"])
```

The model is constrained by a schema. It returns a typed object — not prose. Your code imports it directly. No regex. No `try/except json.loads()`. No hoping.

---

## The Three Levers

| Lever | What it controls | The rule |
|-------|-----------------|----------|
| **Prompt engineering** | What the model tries to do | System message = constitution. User message = task. |
| **Schema constraint** | What shape the output must have | Pydantic model + `with_structured_output()`. |
| **Inference parameters** | How deterministic the output is | `temperature=0` for structured output. |

---

## What You'll Build Today

Open `src/schemas.py`. It's currently a stub. By the end of the session, it will:

1. Define a `BuildCheck` Pydantic model
2. Call the LLM with `with_structured_output()`
3. Return a typed object your code can import — not prose

**You'll also:** vary temperature, break the schema on purpose, add a few-shot example, and see what happens. The skill isn't getting it right the first time — it's building systems that survive the breakage.

---

## One Thing to Try

Before the session, open `src/schemas.py`. Look at the stub. Think: *"What fields would a PR review need? What should the model return?"*
