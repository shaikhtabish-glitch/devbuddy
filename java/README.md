# DevBuddy — Java CLI

> **Language Shepherd:** [TBD]
> **Blueprint Ready:** Week 0 | **Engineers can use from:** Week 0

## Quick Start

```bash
cd java

# Set your API key
export OPENROUTER_API_KEY=sk-or-your-key-here
# Optional: override the model
# export DEVBUDDY_MODEL=anthropic/claude-3.5-sonnet

# Build + run
mvn package -DskipTests -q
java -jar target/devbuddy-0.1.0.jar
```

Output:

```
============================================================
  DevBuddy Verification — Week 0 (Java)
============================================================

[1/3] Checking: auth-service...
  Status:      passing
  Confidence:  30%
  Reason:      I don't have real CI access...
  Tokens:      147 (102 in / 45 out)
  Cost:        $0.000042
  Time:        1.23s
  Type:        BuildCheck ← typed record, not a string!

============================================================
  ✅ VERIFICATION PASSED
  Java:       21.0.1
  Model:      openai/gpt-4o-mini
  Total tokens: 441
  Total cost:   $0.000126
============================================================
```

## Stack

| Layer | Choice |
|-------|--------|
| LLM Provider | OpenRouter (via Spring AI `spring-ai-openai`) |
| DI Container | Spring Framework `AnnotationConfigApplicationContext` |
| Validation / Structured Output | Java records + Jackson |
| Build Tool | Maven (no Boot, no embedded server) |

## Architecture

```
┌──────────────────────────────────────────────────┐
│  Verification.main()                             │
│    │                                              │
│    ├─ new AnnotationConfigApplicationContext(AppConfig)  │
│    │     │                                        │
│    │     ├─ @Bean OpenAiApi     ← OPENROUTER_API_KEY   │
│    │     ├─ @Bean ChatModel     ← OpenRouter base URL  │
│    │     └─ @Bean ChatClient    ← wraps ChatModel      │
│    │                                              │
│    ├─ chatClient.prompt().call().chatResponse()   │
│    │     │                                        │
│    │     ├─ → OpenRouter → model response         │
│    │     ├─ Jackson parse → BuildCheck record     │
│    │     ├─ Usage metadata → CostTracker.cost()   │
│    │     └─ log.info(...) per-call report         │
│    │                                              │
│    └─ Summary: tokens, cost, ✓ PASSED             │
└──────────────────────────────────────────────────┘
```

No Spring Boot. No embedded web server. No `application.yml`. Just Spring IoC + Spring AI.

## Project Structure

```
java/
├── pom.xml
├── README.md
└── src/main/
    ├── java/devbuddy/
    │   ├── Verification.java           # Entry point + verification loop
    │   ├── config/
    │   │   └── AppConfig.java          # @Configuration — wires OpenAiApi, ChatModel, ChatClient
    │   ├── schemas/
    │   │   └── BuildCheck.java         # Typed record (Jackson serialization)
    │   └── cost/
    │       └── CostTracker.java        # Token → cost calculation
    └── resources/
        └── logback.xml                 # Clean console logging (%msg%n)
```

## Differences from Python / Node.js

| Concept | Python | Node.js | Java |
|---------|--------|---------|------|
| LLM Client | `ChatOpenAI(...)` | `new ChatOpenAI({...})` | `OpenAiApi.builder()` + `OpenAiChatModel.builder()` |
| DI | None (module imports) | None (module imports) | `@Configuration` + `@Bean` → `AnnotationConfigApplicationContext` |
| Config | `load_dotenv()` | `dotenv.config()` | `System.getenv("OPENROUTER_API_KEY")` |
| Structured output | `with_structured_output()` | `withStructuredOutput()` | `chatResponse()` → Jackson `readValue()` |
| Cost tracking | Inline in verification | `config.js` export | `CostTracker` static utility |
| Entry point | `if __name__ == "__main__"` | `main().catch(...)` | `Verification.main()` bootstraps Spring context |

## Each Week

```bash
cd java

# Pull latest from upstream
git pull upstream main

# Read the task
cat ../docs/week-NN.md

# Build in src/main/java/devbuddy/
# Run:
mvn package -DskipTests -q && java -jar target/devbuddy-0.1.0.jar
```
