"""
Demo 3: Tool Failure — Retry in the app layer, not the prompt

THE POINT OF THIS DEMO: tools fail and models misbehave. Retry, denial,
and fallback are CODE decisions — deterministic, testable, auditable.
The prompt is the wrong place for safety. The model only ever sees the
final result: success or a structured error.

  Act 1 — Retry in the app layer: normal → transient (retry) → exhausted.
  Act 2 — The guardrail: hostile/unknown tool calls are DENIED by code.
  Act 3 — The model sees the error: feed it the structured error and watch
          it degrade gracefully.

Run: python scripts/week-04/demo-03-tool-failure.py
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage

from src.tools import build_status, flaky, execute_tool_safely
from src.llm import get_llm

BORDER = "=" * 70


def pause(prompt: str = "  ⏸  Press Enter to continue… ") -> None:
    """Pause so the learner can predict before the reveal."""
    try:
        input(prompt)
    except EOFError:
        print()


def flaky_status_registry(fail_first_n: int) -> dict:
    """A registry that maps get_build_status → a flaky wrapper of build_status.

    The wrapper is built from the RAW function in src.tools (flaky()), so the
    data stays in one place — only the failure behaviour is injected.
    """
    impl = flaky(build_status, fail_first_n=fail_first_n)

    @tool
    def get_build_status(service_name: str) -> str:
        """Return the current build/health status of a service."""
        return impl(service_name)

    return {"get_build_status": get_build_status}


print(BORDER)
print("  Demo 3: Tool Failure — Retry & Denial Live in the App Layer")
print(BORDER)
print()
print("  The model proposes a call. YOUR code decides whether it runs,")
print("  whether it retries, and what the model sees. Nothing here lives")
print("  in the prompt.")
print()

# ═══════════════════════════════════════════════════════════════
# Act 1 — Retry in the app layer (deterministic, no LLM in the loop)
# ═══════════════════════════════════════════════════════════════
print("  ── Act 1: Retry in the app layer ────────────────────────────")
print()
print("  The same call, three times — only the failure behaviour changes:")
print("  flaky(build_status, fail_first_n=N) wraps the RAW function.")
print()
tool_call = {"name": "get_build_status", "args": {"service_name": "payment-api"}}

scenarios = [
    (0, "normal",     "tool never fails"),
    (1, "transient",  "fails once, then recovers"),
    (99, "exhausted", "always fails — retries burn out"),
]

for fail_first_n, label, meaning in scenarios:
    print(f"  ── scenario: {label:<10} ({meaning}) ──")
    result = execute_tool_safely(
        tool_call,
        max_retries=2,                       # 1 initial + 2 retries
        tools_by_name=flaky_status_registry(fail_first_n),
        verbose=True,
    )
    parsed = json.loads(result)
    if "error" in parsed:
        print(f"     ❌ structured error after {parsed['attempts']} attempts:")
        print(f"        {parsed['error']}")
    else:
        print(f"     ✅ returned: {result[:110]}")
    print()

print("  Retries ran inside execute_tool_safely() — your code, not the")
print("  model's. The model never saw the failure; it only ever sees the")
print("  final result: success, or a structured error.")
print()

# ═══════════════════════════════════════════════════════════════
# Act 2 — The guardrail: never trust the raw tool request
# ═══════════════════════════════════════════════════════════════
print("  ── Act 2: The guardrail — never trust the raw request ───────")
print()
print("  The model returns {name, args}. That is a REQUEST, not a fact.")
print("  Your registry decides if it deserves to become an action.")
print()
print("  ⏸  PAUSE & PREDICT: the model asks for 'delete_production_db'.")
print("     What should happen? Predict, then continue.")
pause()
print()

hostile = execute_tool_safely({"name": "delete_production_db", "args": {}})
print(f"  Request: delete_production_db({{}})")
print(f"  Response: {hostile}")
print("  → DENIED by the registry. The model can never reach code it was")
print("    not given — that is what the whitelist is for.")
print()

unknown_service = execute_tool_safely(
    {"name": "get_build_status", "args": {"service_name": "ghost-service"}})
print(f"  Request: get_build_status(ghost-service)")
print(f"  Response: {unknown_service}")
print("  → A valid tool with bad args returns a structured 'no data' result.")
print("    No crash, no exception — the model can reason about it.")
print()

# ═══════════════════════════════════════════════════════════════
# Act 3 — The model sees the error (one LLM call)
# ═══════════════════════════════════════════════════════════════
print("  ── Act 3: The model sees the error ──────────────────────────")
print()
print("  Now the app-layer error is fed to the model. The model's job is")
print("  to degrade gracefully — tell the user what happened, not to")
print("  magically 'fix' the tool.")
print()
exhausted = execute_tool_safely(
    {"name": "get_build_status", "args": {"service_name": "payment-api"}},
    max_retries=2,
    tools_by_name=flaky_status_registry(99),
)
llm = get_llm(temperature=0.0)
answer = llm.invoke([
    SystemMessage(content=(
        "You are an engineering assistant. A monitoring tool was called but "
        "returned a structured error. Report to the user what happened and "
        "what the next step should be. Do not invent data."
    )),
    HumanMessage(content=f"Question: Is the payment-api healthy?\n\nTool result:\n{exhausted}"),
])
print(f"  Structured error given to model:")
print(f"     {exhausted}")
print(f"  Model's answer: {answer.content.strip()}")
print()

print(BORDER)
print("  THE MESSAGE: retry logic, denial, and error format are CODE")
print("  decisions — deterministic, testable, auditable. The model's")
print("  recovery is unreliable by design; your application layer is what")
print("  ships. Never trust the raw tool request; always route execution")
print("  through your own guardrail.")
print()
print("  YOUR TURN:")
print("    • Change max_retries in Act 1 and watch the attempts count move.")
print("    • Add a retry-with-backoff for the exhausted case — should the")
print("      app retry 3 times, or fail fast and escalate? Why?")
print(BORDER)
