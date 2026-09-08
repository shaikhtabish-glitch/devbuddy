"""
Demo 1: Tool Call — Wire a tool, watch the model call it

THE POINT OF THIS DEMO is not that the model called a function — it is
that the model could NOT have run it. It returned a request
({name, args}); your code did the work. The model proposes.
Your code disposes.

Walks the loop by hand: bind a tool, ask, see the request the model
returns, execute it yourself, inject the result, get the answer.

Run: python scripts/week-04/demo-01-tool-call.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from src.llm import get_llm


@tool
def get_build_status(service_name: str) -> str:
    """Return the current build status for a given service."""
    statuses = {
        "auth-service": {"status": "healthy", "last_deploy": "2026-06-28T08:15:00Z"},
        "payment-api": {"status": "degraded", "last_deploy": "2026-06-28T06:45:00Z"},
        "inventory-service": {"status": "unknown", "last_deploy": "2026-06-20T11:00:00Z"},
    }
    data = statuses.get(service_name, {"status": "unknown", "error": f"No data for '{service_name}'"})
    return json.dumps(data)

print("=" * 70)
print("  Demo 1: Wire a Tool → Watch the Model Call It")
print("=" * 70)
print()

# ── Step 1: Bind the tool ─────────────────────────────────────
llm = get_llm(temperature=0)
llm_with_tools = llm.bind_tools([get_build_status])

# ── Step 2: Ask a question that needs the tool ────────────────
question = "Is the payment-api healthy?"
print(f"  User: {question}")
print()

response = llm_with_tools.invoke([HumanMessage(content=question)])

print(f"  Model decided to call: {response.tool_calls[0]['name']}")
print(f"  With arguments:         {response.tool_calls[0]['args']}")
print()

# ── Step 3: Execute the tool ───────────────────────────────────
result = get_build_status.invoke(response.tool_calls[0]["args"])
print(f"  Tool returned: {result}")
print()

# ── Step 4: Inject result, get final answer ────────────────────
messages = [
    HumanMessage(content=question),
    response,
    ToolMessage(content=result, tool_call_id=response.tool_calls[0]["id"]),
]
final = llm_with_tools.invoke(messages)
print(f"  Model: {final.content}")
print()
print("=" * 70)
print("  The loop: Request → Decide → Execute → Return → Answer")
print("  THE BOUNDARY: the model could NOT have run get_build_status.")
print("  It returned a request. Your code executed it. You decide whether")
print("  a request becomes an action — and you keep the trace.")
print("  The model proposes. Your code disposes.")
print("=" * 70)
