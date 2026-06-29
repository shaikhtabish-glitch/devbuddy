"""
Demo 3: Tool Failure — Three scenarios, deterministic

Run 1: Tool succeeds normally.
Run 2: Tool fails once, retry succeeds (resilience).
Run 3: Tool fails all retries, returns structured error (graceful degradation).

Shows application-layer error handling keeping the system running
when tools fail — retry logic, fallback, and structured errors.

Run: python scripts/week-04/demo-03-tool-failure.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from src.llm import get_llm

# ── Tool with controllable failure ────────────────────────────

_fail_count = 0

@tool
def get_build_status(service_name: str) -> str:
    """Return the current build health of a service."""
    global _fail_count
    _fail_count += 1
    # Run 1: success. Run 2: fail once then succeed. Run 3: fail always.
    if _fail_count == 2:   # first call of Run 2 → fail once
        raise ConnectionError(f"Monitoring API unreachable for '{service_name}'")
    if _fail_count >= 4:   # Run 3 onwards → always fail
        raise ConnectionError(f"Monitoring API unreachable for '{service_name}'")
    return json.dumps({"status": "degraded", "last_deploy": "2026-06-28T06:45:00Z"})


def execute_tool_safely(tool_call, tools_map, max_retries=2):
    """Application-layer error handling: retry, then return structured error."""
    tool_name = tool_call["name"]
    tool_fn = tools_map.get(tool_name)
    if tool_fn is None:
        return json.dumps({"error": f"Unknown tool: '{tool_name}'"})

    for attempt in range(1, max_retries + 2):
        try:
            return tool_fn.invoke(tool_call["args"])
        except Exception as e:
            if attempt <= max_retries:
                print(f"       ⚠️  Attempt {attempt} failed, retrying...")
                continue
            return json.dumps({
                "error": str(e),
                "tool": tool_name,
                "status": "failed",
                "attempts": max_retries + 1,
                "hint": "The tool is temporarily unavailable.",
            })


TOOLS = [get_build_status]
TOOLS_MAP = {t.name: t for t in TOOLS}

llm = get_llm(temperature=0)
llm_with_tools = llm.bind_tools(TOOLS)

scenarios = [
    ("normal", "Tool succeeds on first call. Happy path."),
    ("retry", "Tool fails once, retry succeeds. Resilience."),
    ("exhausted", "Tool fails all retries. Graceful degradation."),
]

print("=" * 70)
print("  Demo 3: Tool Failure — Three Deterministic Scenarios")
print("=" * 70)
print()

for label, description in scenarios:
    question = "Is the payment-api healthy?"
    print(f"  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║  SCENARIO: {label:<12} — {description:<36} ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝")
    print()

    response = llm_with_tools.invoke([HumanMessage(content=question)])

    print(f"       Query:  {question}")
    print(f"       Decide: model calls get_build_status('payment-api')")

    if response.tool_calls:
        messages = [HumanMessage(content=question), response]
        for tc in response.tool_calls:
            result = execute_tool_safely(tc, TOOLS_MAP)
            parsed = json.loads(result)
            if "error" in parsed:
                print(f"       Result: ❌ FAILED after {parsed['attempts']} attempts")
                print(f"               {parsed['error']}")
            else:
                print(f"       Result: ✅ {result}")
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))
        final = llm_with_tools.invoke(messages)
        print(f"       Answer: {final.content}")
    print()

print("=" * 70)
print("  Scenario 1 → happy path. Tool works, model answers.")
print("  Scenario 2 → transient failure. Retry succeeds. User never knows.")
print("  Scenario 3 → persistent failure. Structured error returned.")
print("               Model gracefully handles the degradation.")
print()
print("  YOUR CODE controls retry logic, fallback, and error format.")
print("  The model only sees the final result — success or structured error.")
print("=" * 70)
