# Week 2 — Structured Outputs & Inference Parameters

**Goal:** Make the LLM return typed, validated objects — not prose.

---

## Setup

```bash
cd python
source .venv/bin/activate
git pull upstream main          # get latest code + test data
pip install -r requirements-dev.txt   # install pytest
```

Verify you're ready:

```bash
python -m pytest tests/ -v      # should show 10 tests, all passing
```

---

## What You'll Build

Open `src/schemas.py`. Currently a stub. By the end of this session, it will:
- Define a `BuildCheck` Pydantic model
- Call the LLM with `with_structured_output()`
- Return a typed object your code can import directly
- Handle schema validation failures

## Files You'll Touch
- `src/schemas.py` — your implementation
- `src/llm.py` — already built (import it: `from src.llm import get_llm`)

## Test Data
- `shared/data/sample-diff.txt` — a clean PR diff
- `shared/data/ambiguous-diff.txt` — an edge case (for self-learning)

---

## Steps

1. Define a `BuildCheck` model with fields: `project`, `severity`, `summary`, `affected_files`
2. Create `analyze_pr(title, diff)` that calls the LLM with structured output
3. Run it against `sample-diff.txt` — you should get a typed object
4. Break the schema (remove a field) — watch validation catch it
5. Add a few-shot example — observe improved adherence
6. Vary temperature (0 → 0.7 → 1.0) — observe output drift

## Acceptance Criteria
- [ ] `analyze_pr()` returns a `BuildCheck` object, not a string
- [ ] Schema validation catches malformed output
- [ ] `temperature=0` produces deterministic output
- [ ] Cost counter prints token usage

## Self-Learning (Before Week 3)
- Add auto-retry (max 3 attempts) on validation failure
- Feed it the ambiguous diff and document: (a) what broke, (b) what the model guessed, (c) what you'd change for production safety, (d) which inference parameter you'd tune and why, (e) how your prompt changed from v1 to v3

## Runbook Contribution
Write a 1-paragraph ADR: "We chose temperature=0 for structured output because…"
