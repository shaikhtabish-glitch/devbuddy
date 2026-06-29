"""
Demo 2: Tool Routing — Two tools, model picks the right one

Adds a second tool and asks a question that requires the model
to choose between them. Shows what happens when it picks wrong.

Run: python scripts/week-04/demo-02-tool-routing.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from src.llm import get_llm


@tool
def get_build_status(service_name: str) -> str:
    """Return the current build health of a service. Status: healthy/degraded/down/unknown."""
    statuses = {
        "auth-service": {"status": "healthy", "last_deploy": "2026-06-28T08:15:00Z"},
        "payment-api": {"status": "degraded", "last_deploy": "2026-06-28T06:45:00Z"},
    }
    return json.dumps(statuses.get(service_name, {"status": "unknown"}))


@tool
def get_recent_deploys(service_name: str, limit: int = 5) -> str:
    """Return the last N deployments for a service. Each has sha, author, timestamp, status."""
    deploys = {
        "payment-api": [
            {"sha": "def789", "status": "success", "timestamp": "2026-06-28T06:45:00Z"},
            {"sha": "jkl345", "status": "rolling_back", "timestamp": "2026-06-27T22:00:00Z"},
        ],
    }
    return json.dumps(deploys.get(service_name, [])[:limit], indent=2)

TOOLS = [get_build_status, get_recent_deploys]
TOOLS_MAP = {t.name: t for t in TOOLS}

llm = get_llm(temperature=0)
llm_with_tools = llm.bind_tools(TOOLS)

print("=" * 70)
print("  Demo 2: Two Tools — Model Picks the Right One")
print("=" * 70)
print()

questions = [
    "Is the auth-service healthy?",
    "Show me the recent deployments for payment-api.",
    "What was deployed recently and is everything healthy?",
]

for q in questions:
    print(f"  User: {q}")
    response = llm_with_tools.invoke([HumanMessage(content=q)])

    if response.tool_calls:
        messages = [HumanMessage(content=q), response]
        for tc in response.tool_calls:
            tool_fn = TOOLS_MAP[tc["name"]]
            result = tool_fn.invoke(tc["args"])
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))
            print(f"  → Called: {tc['name']}({tc['args']})")
        final = llm_with_tools.invoke(messages)
        print(f"  Model: {final.content}")
    else:
        print(f"  → No tool called. Model answered directly.")
    print()

print("=" * 70)
print("  Q1 needed build status → model called get_build_status ✅")
print("  Q2 needed deploy history → model called get_recent_deploys ✅")
print("  Q3 needed both → model's choice depends on tool descriptions")
print("=" * 70)
