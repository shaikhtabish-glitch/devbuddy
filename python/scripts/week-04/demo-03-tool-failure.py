"""
Demo 3: Tool Failure — Break a tool, handle in application layer

Shows what happens when a tool fails, and how application-layer
error handling keeps the system running.

Run: python scripts/week-04/demo-03-tool-failure.py
"""
import os, sys, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from src.llm import get_llm


@tool
def get_build_status(service_name: str) -> str:
    """Return the current build health of a service."""
    if random.random() < 0.4:  # 40% failure rate — demo shows both success and failure
        raise ConnectionError(f"Monitoring API unreachable for '{service_name}'")
    statuses = {"auth-service": "healthy", "payment-api": "degraded"}
    return json.dumps(statuses.get(service_name, {"status": "unknown"}))


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
                print(f"  ⚠️  Attempt {attempt} failed, retrying...")
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

print("=" * 70)
print("  Demo 3: Tool Failure — Handle in Application Layer")
print("=" * 70)
print()

for i in range(3):
    question = "Is the payment-api healthy?"
    print(f"  Run {i+1} — User: {question}")

    response = llm_with_tools.invoke([HumanMessage(content=question)])

    if response.tool_calls:
        messages = [HumanMessage(content=question), response]
        for tc in response.tool_calls:
            result = execute_tool_safely(tc, TOOLS_MAP)
            parsed = json.loads(result)
            if "error" in parsed:
                print(f"  ❌ Tool failed after retries: {parsed['error'][:60]}...")
            else:
                print(f"  ✅ Tool succeeded: {result}")
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))
        final = llm_with_tools.invoke(messages)
        print(f"  Model: {final.content}")
    print()

print("=" * 70)
print("  The model might retry, apologize, or suggest alternatives.")
print("  But YOUR CODE controls retry logic — not the model.")
print("  Application-layer error handling is what ships.")
print("=" * 70)
