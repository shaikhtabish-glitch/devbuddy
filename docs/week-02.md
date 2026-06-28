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

The moderator will run two demos first. Watch them, then follow these steps on your own machine.

---

### Step 1: Reproduce the happy path (10 min)

Open a Python shell or write a quick script. Call `analyze_pr()` with the sample diff:

```python
from src.schemas import analyze_pr

with open("../shared/data/sample-diff.txt") as f:
    diff = f.read()

result = analyze_pr("Fix login redirect loop in auth-service", diff, temperature=0.0)

print(type(result))          # <class 'src.schemas.BuildCheck'> — not str!
print(result.project)        # 'auth-service'
print(result.severity)       # 'critical' (touches auth)
print(result.summary)        # one-sentence summary
print(result.affected_files) # ['src/auth.py', 'tests/test_auth.py']

# Pretty-print the whole thing
print(result.model_dump_json(indent=2))
```

**Do you see a `BuildCheck` object?** Thumbs up. You've just made the LLM return a typed contract. Move on.

**Did it fail?** Check: are you in `build/python/`? Is your `.env` set? Does `python -c "from src.llm import get_llm; get_llm()"` work? Ask a neighbour or the moderator.

---

### Step 2: Break the schema (10 min)

Open `src/schemas.py`. In the `BuildCheck` class, **delete the `severity` field**. Save the file. Run Step 1 again.

```python
# severity is gone from BuildCheck. What happens?
result = analyze_pr("Fix login bug", "changed auth.py", temperature=0.0)
# The model may still return JSON with 'severity' in it, or without it.
# If it's missing, Pydantic raises ValidationError.
```

Now **delete severity from the system prompt too** (the string inside `SystemMessage`). Run again. Does the model still include it?

Now **add a few-shot example** to the system prompt:

```python
SystemMessage(content=(
    "You are a code reviewer. Return a BuildCheck.\n"
    "Example: {\"project\": \"api-gateway\", \"severity\": \"medium\", "
    "\"summary\": \"Added rate limiting\", \"affected_files\": [\"gateway.py\"]}\n"
    "- severity: 'critical' if auth/payments/security. 'high' for core logic. "
    "'medium' for feature work. 'low' for docs/typos.\n"
    ...
))
```

Run once without the example, once with it. **Does the few-shot example improve adherence?** The prompt is code — small changes have big effects.

---

### Step 3: Vary temperature (5 min)

Same `analyze_pr()` call. Same input. Change only `temperature`:

```python
for temp in [0.0, 0.3, 0.7, 1.0]:
    result = analyze_pr("Fix login bug", "changed auth.py", temperature=temp)
    print(f"temp={temp}: severity={result.severity}  summary={result.summary}")
```

At temp=0: deterministic. Same output every run.
At temp=0.3–0.7: summary wording drifts. Severity holds (contract).
At temp=1.0: wider drift. Severity might flip on a more ambiguous diff.

Try it with `ambiguous-diff.txt` instead — no auth/payments/security keywords. Severity becomes a genuine judgment call. Temperature now changes the answer.

---

### Step 4: Truncate with max_tokens (5 min)

`analyze_pr()` accepts `max_tokens`. Crank it down until the output breaks:

```python
for limit in [200, 50, 20, 10]:
    try:
        result = analyze_pr("Fix bug", "changed app.py", temperature=0.0, max_tokens=limit)
        print(f"max_tokens={limit:>3}: ✅ {result.severity}")
    except Exception as e:
        print(f"max_tokens={limit:>3}: ❌ truncated — {e}")
```

At 200: works fine. At 50: might fail. At 10: guaranteed to fail — the model can't fit a valid `BuildCheck` JSON into 10 tokens. **max_tokens is a cost guard, but set it too low and your pipeline breaks.** Measure your schema's token footprint, don't guess.

---

### Step 5: Explore the code (remaining time)

If you finish early, explore what's already in the codebase for later weeks:

```bash
# See the composed schema you'll work with in self-learning
python scripts/week-02/explore-readiness-report.py

# Run the inference parameter demo the moderator showed
python scripts/week-02/demo-03-inference-parameters.py

# Read the source of the raw-vs-pydantic demo
cat scripts/week-02/demo-02-raw-vs-pydantic.py

# Run pure-Pydantic tests (no API calls, instant)
python -m pytest tests/test_schemas.py -v -k "not analyze_pr"
```

---

## Acceptance Criteria

By the end of the session, you should be able to:

- [ ] Call `analyze_pr()` and get back a `BuildCheck` — not a string, not a dict, a typed object
- [ ] Delete a field from the schema and see Pydantic raise `ValidationError`
- [ ] Run the same call at `temperature=0` twice and get the same output
- [ ] Run at `temperature=0.7` and see the summary wording change
- [ ] Set `max_tokens=10` and watch the call fail with a truncation error
- [ ] Explain to a teammate: *"Raw JSON prompting is a request. Pydantic is a contract."*

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
