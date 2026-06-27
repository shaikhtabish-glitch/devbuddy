# Week 2 — Structured Outputs & Prompt Engineering

**Goal:** Make the LLM return typed, validated JSON — not prose.

## What You'll Build
Open `src/schemas.py`. Currently a stub. By the end of this session, it will:
- Define Pydantic models (or Zod schemas / Java records)
- Call the LLM with `with_structured_output()`
- Validate the response against your schema
- Auto-retry on validation failure

## Files You'll Touch
- `python/src/schemas.py` — your implementation
- `python/src/llm.py` — already built (OpenRouter client — import it, don't rewrite it)

## Test Data
- `shared/data/sample-diff.txt` — a clean PR diff for testing
- `shared/data/ambiguous-diff.txt` — an edge case (for self-learning)

## Steps
1. Define a `BuildCheck` (or equivalent) model
2. Create a function that calls the LLM with structured output
3. Run it against `sample-diff.txt` — you should get valid JSON
4. Break the schema intentionally — watch validation catch it
5. Add a few-shot example — observe improved adherence
6. Vary temperature (0 → 0.7 → 1.0) — observe output drift

## Acceptance Criteria
- [ ] `analyze_pr()` returns a typed object, not a string
- [ ] Schema validation catches malformed output
- [ ] Cost counter prints token usage
- [ ] Temperature=0 produces deterministic output

## Self-Learning (Before Week 3)
- Add auto-retry (max 3 attempts) on validation failure
- Upgrade to a fully typed object that fails loudly on drift
- Feed it the ambiguous diff and document what broke

## Runbook Contribution
Write a 1-paragraph ADR: "We chose temperature=0 for structured output because…"
