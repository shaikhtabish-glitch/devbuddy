# Week 2 — Structured Outputs & Inference Parameters

**Goal:** Make the LLM return typed, validated objects — not prose.

**The ladder** (fragile → reliable): prompt + parse → JSON mode → **structured output** (this week) → function calling (Week 4). Structured output is the first rung that guarantees *fields*, not just syntax.

---

## Setup

### Python

```bash
cd python
python install.py                  # one-command setup (prefers uv, falls back to pip)
git pull upstream main          # get latest code + test data
uv pip install -r requirements-dev.txt   # install pytest
```

Verify you're ready:

```bash
python -m pytest tests/test_schemas.py -v -k "not analyze_pr"
# Should show 8 tests passing (pure Pydantic — no API calls, instant)

python -m pytest tests/test_schemas.py -v
# All 12 tests — includes 4 that call OpenRouter (requires API key)
```

### Node.js

```bash
cd nodejs
git pull upstream main          # get latest code + test data
npm install
```

Verify you're ready:

```bash
npx vitest run tests/test_schemas.js -t "ServiceReadinessReport|BuildCheck"
# 11 tests passing (pure Zod — no API calls, instant)

npx vitest run tests/test_schemas.js
# All 15 tests — includes 4 that call OpenRouter (requires API key)
```

### Java

```bash
cd java
git pull upstream main          # get latest code + test data
# set openrouter.api.key=sk-or-... in src/main/resources/application.properties
```

Verify you're ready:

```bash
mvn test -Dtest=SchemasTest
# 15 tests passing (pure records/Jackson — no API calls, instant)

mvn test -Dtest=SchemasLlmTest
# 4 tests that call OpenRouter (requires API key)
```

---

## What You Have

Open `src/schemas.py` (Python), `src/schemas.js` (Node.js), or `schemas/JsonSchemas.java` + `schemas/SchemasService.java` (Java). Each contains **two schema families**:

| Schema | Shape | Purpose |
|--------|-------|---------|
| `BuildCheck` | Flat — 4 fields (`project`, `severity`, `summary`, `affected_files`) | In-session exercise. You'll break it, vary temperature, add few-shot examples. |
| `ServiceReadinessReport` | Composed — 5 nested models, optional fields, cross-field validators | Self-learning. This is what DevBuddy produces at Week 7. No API calls needed — test with mock JSON. |

## Files You'll Touch

| Python | Node.js | Java | Purpose |
|--------|---------|------|---------|
| `src/schemas.py` | `src/schemas.js` | `schemas/JsonSchemas.java`, `schemas/SchemasService.java` | Study the two schemas, extend `BuildCheck` during hands-on |
| `src/llm.py` | `src/llm.js` | `config/AppConfig.java` | Already built (LLM client factory) |
| `tests/test_schemas.py` | `tests/test_schemas.js` | `SchemasTest.java`, `SchemasLlmTest.java` | Add your own test cases |

## Test Data
- `shared/data/sample-diff.txt` — a clean PR diff (for `BuildCheck`)
- `shared/data/ambiguous-diff.txt` — an edge case (for self-learning)
- `shared/data/service-readiness-healthy.json` — mock healthy service
- `shared/data/service-readiness-degraded.json` — mock degraded service
- `shared/data/service-readiness-unknown.json` — mock unknown service

## Demo Scripts

| Python | Node.js | Java (`mvn -q compile exec:java -Dexec.mainClass=…`) |
|--------|---------|------------------------------------------------------------------|
| `python scripts/week-02/demo-01-prose-vs-structured.py` | `node scripts/week-02/demo-01-prose-vs-structured.js` | `devbuddy.scripts.week02.Demo01ProseVsStructured` |
| `python scripts/week-02/demo-02-raw-vs-pydantic.py` | `node scripts/week-02/demo-02-raw-vs-zod.js` | `devbuddy.scripts.week02.Demo02RawVsStructured` |
| `python scripts/week-02/demo-03-inference-parameters.py` | `node scripts/week-02/demo-03-inference-parameters.js` | `devbuddy.scripts.week02.Demo03InferenceParameters` |
| `python scripts/week-02/demo-04-sketchpad.py` | `node scripts/week-02/demo-04-sketchpad.js` | `devbuddy.scripts.week02.Demo04Sketchpad` |
| `python scripts/week-02/demo-05-agentic-retry.py` | `node scripts/week-02/demo-05-agentic-retry.js` | `devbuddy.scripts.week02.Demo05AgenticRetry` |
| `python scripts/week-02/explore-readiness-report.py` | `node scripts/week-02/explore-readiness-report.js` | `devbuddy.scripts.week02.ExploreReadinessReport` |

---

## In-Session Steps

The moderator will run two demos first. Watch them, then follow these steps on your own machine.

---

### Step 1: Reproduce the happy path (10 min)

**Python:**

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

**Node.js:**

```js
import { readFileSync } from "fs";
import { analyzePr } from "./schemas.js";

const diff = readFileSync("../shared/data/sample-diff.txt", "utf-8");

const result = await analyzePr({
  title: "Fix login redirect loop in auth-service",
  diff,
  temperature: 0.0,
});

console.log(result.constructor.name);  // Object — not string!
console.log(result.project);           // 'auth-service'
console.log(result.severity);          // 'critical' (touches auth)
console.log(result.summary);
console.log(result.affected_files);

// Pretty-print the whole thing
console.log(JSON.stringify(result, null, 2));
```

**Java:**

```java
// In the demo/test bootstrap (new AnnotationConfigApplicationContext(AppConfig.class)):
SchemasService schemas = ctx.getBean(SchemasService.class);

String diff = Files.readString(Path.of("../shared/data/sample-diff.txt"));
BuildCheck result = schemas.analyzePr(
        "Fix login redirect loop in auth-service", diff, 0.0, null);

System.out.println(result.getClass().getSimpleName()); // BuildCheck — not String!
System.out.println(result.project());                   // 'auth-service'
System.out.println(result.severity().value());          // 'critical' (touches auth)
System.out.println(result.summary());                   // one-sentence summary
System.out.println(result.affectedFiles());             // [src/auth.py, tests/test_auth.py]
```

**Do you see a typed object?** Thumbs up. You've just made the LLM return a typed contract.

---

### Step 2: Break the schema (10 min)

Open your schema file. In the `BuildCheck` class / schema, **delete the `severity` field**. Save. Run Step 1 again.

Now **delete severity from the system prompt too**. Run again. Does the model still include it?

Now **add a few-shot example** to the system prompt — an example with all four fields. Run once without the example, once with it. **Does the few-shot example improve adherence?**

> Few-shot is enough for *format* adherence (what we're testing here). For *content* quality, you'd need a dozen+ examples that match production data — an n-shot problem, and what evals (Week 7) are for.

---

### Step 3: Vary temperature (5 min)

Same input. Change only `temperature`:

**Python:**

```python
for temp in [0.0, 0.3, 0.7, 1.0]:
    result = analyze_pr("Fix login bug", "changed auth.py", temperature=temp)
    print(f"temp={temp}: severity={result.severity}  summary={result.summary}")
```

**Node.js:**

```js
for (const temp of [0.0, 0.3, 0.7, 1.0]) {
  const result = await analyzePr({
    title: "Fix login bug",
    diff: "changed auth.py",
    temperature: temp,
  });
  console.log(`temp=${temp}: severity=${result.severity}  summary=${result.summary}`);
}
```

**Java:**

```java
for (double temp : new double[]{0.0, 0.3, 0.7, 1.0}) {
    BuildCheck r = schemas.analyzePr("Fix login bug", "changed auth.py", temp, null);
    System.out.println("temp=" + temp + ": severity=" + r.severity().value()
            + "  summary=" + r.summary());
}
```

At temp=0: deterministic. At temp=0.7: summary drifts. At temp=1.0: wider drift.

Key point: the schema guarantees **validity** at every temperature — so `temp=0` is a minor reproducibility dial (consistent phrasing for tests/CI), not a correctness requirement. The parameter that actually bites is `max_tokens` (truncation, next step).

---

### Step 4: Truncate with max_tokens / maxTokens (5 min)

**Python:**

```python
for limit in [200, 50, 20, 10]:
    try:
        result = analyze_pr("Fix bug", "changed app.py", temperature=0.0, max_tokens=limit)
        print(f"max_tokens={limit:>3}: ✅ {result.severity}")
    except Exception as e:
        print(f"max_tokens={limit:>3}: ❌ truncated — {e}")
```

**Node.js:**

```js
for (const limit of [200, 50, 20, 10]) {
  try {
    const result = await analyzePr({
      title: "Fix bug",
      diff: "changed app.py",
      temperature: 0.0,
      maxTokens: limit,
    });
    console.log(`maxTokens=${String(limit).padStart(3)}: ✅ ${result.severity}`);
  } catch (e) {
    console.log(`maxTokens=${String(limit).padStart(3)}: ❌ truncated — ${e.message}`);
  }
}
```

**Java:**

```java
for (int limit : new int[]{200, 50, 20, 10}) {
    try {
        BuildCheck r = schemas.analyzePr("Fix bug", "changed app.py", 0.0, limit);
        System.out.println("maxTokens=" + limit + ": ✅ " + r.severity().value());
    } catch (Exception e) {
        System.out.println("maxTokens=" + limit + ": ❌ truncated — " + e.getMessage());
    }
}
```

At 200: works. At 10: guaranteed to fail. **maxTokens is a cost guard — set it too low and your pipeline breaks.**

---

### Step 5: Explore the code (remaining time)

**Python:**

```bash
python scripts/week-02/explore-readiness-report.py
python scripts/week-02/demo-03-inference-parameters.py
python -m pytest tests/test_schemas.py -v -k "not analyze_pr"
```

**Node.js:**

```bash
node scripts/week-02/explore-readiness-report.js
node scripts/week-02/demo-03-inference-parameters.js
npx vitest run tests/test_schemas.js -t "ServiceReadinessReport|BuildCheck"
```

**Java:**

```bash
mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week02.ExploreReadinessReport
mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week02.Demo03InferenceParameters
mvn test -Dtest=SchemasTest
```

---

## Acceptance Criteria

- [ ] Call `analyzePr()` / `analyze_pr()` and get back a typed object — not prose
- [ ] Delete a field from the schema and see validation reject it
- [ ] Run at `temperature=0` twice and get a consistent verdict
- [ ] Run at `temperature=1.0` twice and still get a *valid* typed object both times — only the phrasing drifts
- [ ] Set maxTokens low enough to trigger a truncation error
- [ ] Explain: *"Raw JSON prompting is a request. Schema-constrained output is a contract."*
- [ ] Explain: *"The schema guarantees validity at any temperature; `max_tokens` (truncation) is the parameter that bites. Valid JSON is step one — the right JSON is step two."*

---

## Self-Learning (Before Week 3)

### Part A: Validate all three scenarios

1. Run the explore script for your language
2. Extend it to load and validate all 3 JSON scenarios
3. Tests are already provided in `tests/test_schemas.py` / `.js` / `SchemasTest.java`
4. Run pure-schema tests — instant feedback, no API calls

### Part B: Call the LLM with mock data

Use `generateReadinessReport()` / `generate_readiness_report()` to feed mock data to the LLM and get back a typed `ServiceReadinessReport`. Compare the LLM's verdict to hand-written JSON. Where does it differ? What prompt changes would improve accuracy?

### Part C: BuildCheck + auto-retry (if time permits)

Add auto-retry (max 3 attempts) on validation failure. Feed it `ambiguous-diff.txt` and document what broke.

---

## Runbook Contribution

Write a 1-paragraph ADR: "For structured output we rely on the schema for validity and choose temperature for determinism vs. judgment — we default to `temperature=0` for reproducible tests and CI because…" (What would make you raise it?)
