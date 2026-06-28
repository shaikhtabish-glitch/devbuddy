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
python -m pytest tests/test_schemas.py -v -k "not analyze_pr"
# Should show 10 tests passing (pure Pydantic — no API calls, instant)

python -m pytest tests/test_schemas.py -v
# All 13 tests — includes 3 that call OpenRouter (requires API key)
```

---

## What You Have

Open `src/schemas.py`. It already contains **two schema families**:

| Schema | Shape | Purpose |
|--------|-------|---------|
| `BuildCheck` | Flat — 4 fields (`project`, `severity`, `summary`, `affected_files`) | In-session exercise. You'll break it, vary temperature, add few-shot examples. |
| `ServiceReadinessReport` | Composed — 5 nested models, `Optional` fields, `field_validator`, `model_validator` | Self-learning. This is what DevBuddy produces at Week 7. No API calls needed — test with mock JSON. |

## Files You'll Touch
- `src/schemas.py` — study the two schemas, extend `BuildCheck` during hands-on
- `src/llm.py` — already built (`get_llm()` factory)
- `tests/test_schemas.py` — add your own test cases

## Test Data
- `shared/data/sample-diff.txt` — a clean PR diff (for `BuildCheck`)
- `shared/data/ambiguous-diff.txt` — an edge case (for self-learning)
- `shared/data/service-readiness-healthy.json` — mock healthy service
- `shared/data/service-readiness-degraded.json` — mock degraded service
- `shared/data/service-readiness-unknown.json` — mock unknown service

## Demo Scripts
- `scripts/week-02/demo-02-prompt-json.py` — prompt JSON breaks at high temperature
- `scripts/week-02/demo-02-raw-vs-pydantic.py` — **the centerpiece**: same input, same temp, raw vs Pydantic
- `scripts/week-02/demo-03-inference-parameters.py` — temp, max_tokens, and cost drill
- `scripts/week-02/validate-readiness.py` — load mock JSON, validate against `ServiceReadinessReport`

---

## In-Session Steps

1. Reproduce `analyze_pr()` against `sample-diff.txt` — you should get a typed `BuildCheck`
2. Break the schema (remove a field) — watch validation catch it
3. Add a few-shot example — observe improved adherence
4. Vary temperature (0 → 0.7 → 1.0) — observe output drift
5. Set `max_tokens=10` — watch structured output get truncated → validation fails

## Acceptance Criteria
- [ ] `analyze_pr()` returns a `BuildCheck` object, not a string
- [ ] Schema validation catches malformed output
- [ ] `temperature=0` produces deterministic output
- [ ] Cost counter prints token usage

---

## Self-Learning (Before Week 3)

### Part 1: BuildCheck + auto-retry
- Add auto-retry (max 3 attempts) on validation failure
- Feed it the ambiguous diff and document: (a) what broke, (b) what the model guessed, (c) what you'd change for production safety, (d) which inference parameter you'd tune and why, (e) how your prompt changed from v1 to v3

### Part 2: ServiceReadinessReport — pure Pydantic
- Run the validation script: `python scripts/week-02/validate-readiness.py`
- It loads 3 mock JSON scenarios (healthy, degraded, unknown) and validates each
- Study the composed schema in `src/schemas.py` — 5 nested models, `field_validator`, `model_validator`
- Add a 4th scenario: write your own JSON file, validate it, document which validators caught what
- Compare the flat `BuildCheck` to the composed `ServiceReadinessReport`:
  - Which would you use for a customer-facing feature? Why?
  - Which teaches you more about Pydantic? Why?

### Part 3: Add tests
- `tests/test_schemas.py` has 8 pure-Pydantic tests for `ServiceReadinessReport`
- Add tests for your new scenario
- Run: `python -m pytest tests/test_schemas.py -v -k "not analyze_pr"` (no API calls, instant feedback)

---

## Runbook Contribution
Write a 1-paragraph ADR: "We chose temperature=0 for structured output because…"
