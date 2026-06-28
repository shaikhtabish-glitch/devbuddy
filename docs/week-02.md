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
# Should show 8 tests passing (pure Pydantic — no API calls, instant)
# (your homework: add tests for the other 2 mock JSON files)

python -m pytest tests/test_schemas.py -v
# All 11 tests — includes 3 that call OpenRouter (requires API key)
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
- `scripts/week-02/demo-02-raw-vs-pydantic.py` — **the centerpiece**: same input, same temp, raw vs Pydantic
- `scripts/week-02/demo-03-inference-parameters.py` — temp, max_tokens, and cost drill
- `scripts/week-02/explore-readiness-report.py` — validate mock JSON + LLM generation lab

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

> **The take-home is `ServiceReadinessReport`.** This is the composed schema — 5 nested models, validators, the capstone output format. You'll validate it with mock data AND call the LLM to generate one.

### Part A: Validate all three scenarios

1. Run the starting script: `python scripts/week-02/explore-readiness-report.py`
   - It validates `service-readiness-healthy.json`. Read the output. Read the TAKE-HOME ASSIGNMENT section at the bottom.
2. Extend it to also load and validate `service-readiness-degraded.json` and `service-readiness-unknown.json`
3. Add tests for both to `tests/test_schemas.py` (follow the healthy example already there)
4. Run: `python -m pytest tests/test_schemas.py -v -k "not analyze_pr"` — all pure-Pydantic tests, instant feedback

### Part B: Call the LLM with mock data

`src/schemas.py` has a new function: `generate_readiness_report(service_name, build_data, deploy_data)`. It takes the mock JSON data, feeds it to the LLM, and returns a typed `ServiceReadinessReport`.

1. Write a short script (or extend `explore-readiness-report.py`) that:
   - Loads one of the mock JSON files
   - Passes the build + deploy data to `generate_readiness_report()`
   - Prints the result with `model_dump_json(indent=2)`
2. Run it for all 3 scenarios. Compare the LLM's verdict to the hand-written JSON:
   - Does the model agree with the human-written verdict? Where does it differ?
   - What would you change in the system prompt to make it more accurate?
   - Try at `temperature=0.7`. Does the verdict change?

### Part C: BuildCheck + auto-retry (if time permits)
- Add auto-retry (max 3 attempts) on validation failure for `analyze_pr()`
- Feed it `ambiguous-diff.txt` and document what broke

---

## Runbook Contribution
Write a 1-paragraph ADR: "We chose temperature=0 for structured output because…"
