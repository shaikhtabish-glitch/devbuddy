"""
Demo 2: Tool Routing — Two tools, model picks the right one

THE POINT OF THIS DEMO: two tools, one question. The model picks — but it
is YOUR descriptions that taught it to pick. Routing is a design problem,
not a model problem. Vague description → vague routing.

  Part A — Observed routing: real tools from src.tools, several questions,
           print what the model ACTUALLY called (it varies run to run).
  Part B — The lever: the same question against VAGUE tool descriptions
           vs PRECISE tool descriptions. Watch routing change.

Run: python scripts/week-04/demo-02-tool-routing.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from src.tools import (
    ALL_TOOLS,
    build_status,
    recent_deploys,
)
from src.llm import get_llm

BORDER = "=" * 70


def pause(prompt: str = "  ⏸  Press Enter to continue… ") -> None:
    """Pause so the learner can predict before the reveal."""
    try:
        input(prompt)
    except EOFError:
        print()


def decide_calls(question: str, tools: list) -> list:
    """Ask the model once with tools bound; return the observed tool calls."""
    llm = get_llm(temperature=0.0)
    response = llm.bind_tools(tools).invoke([HumanMessage(content=question)])
    return response.tool_calls or []


def print_calls(calls: list) -> None:
    if not calls:
        print("       → NO tool called — the model answered directly.")
        return
    for tc in calls:
        print(f"       → {tc['name']}({tc['args']})")


# ── Part B tool variants: same tools, two levels of description ──

@tool("get_build_status", description="Get service information.")
def _vague_status(service_name: str) -> str:
    return build_status(service_name)


@tool("get_recent_deploys", description="Get records.")
def _vague_deploys(service_name: str, limit: int = 5) -> str:
    return recent_deploys(service_name, limit)


@tool("get_build_status",
      description=("Return the current build/health status for a service: "
                   "'healthy', 'degraded', 'down', or 'unknown', plus last deploy "
                   "time. Use for questions like 'is X healthy?'"))
def _precise_status(service_name: str) -> str:
    return build_status(service_name)


@tool("get_recent_deploys",
      description=("Return the last N deployments for a service (sha, author, "
                   "timestamp, status). Use for questions like 'what was deployed "
                   "recently for X?' or 'is X healthy?'"))
def _precise_deploys(service_name: str, limit: int = 5) -> str:
    return recent_deploys(service_name, limit)


VAGUE = [_vague_status, _vague_deploys]
PRECISE = [_precise_status, _precise_deploys]

print(BORDER)
print("  Demo 2: Tool Routing — Observed, then the Description Lever")
print(BORDER)
print()

# ═══════════════════════════════════════════════════════════════
# Part A — Observed routing over the real tools
# ═══════════════════════════════════════════════════════════════
print("  ── Part A: Observed routing (real tools from src.tools) ────")
print()
print("  Four questions, one LLM call each. Read what the model ACTUALLY")
print("  calls — outcomes vary run to run, so classify, don't assume.")
print()
print("  ⏸  PAUSE & PREDICT: for each question below, which tool should it")
print("     call? Write your guess, then continue.")
pause()
print()

questions = [
    "Is the auth-service healthy?",
    "What were the last 2 deployments for payment-api?",
    "Are there any active incidents for inventory-service?",
    "What's the latest build status?",  # deliberately ambiguous — no service
]

for q in questions:
    print(f"  User: {q}")
    calls = decide_calls(q, ALL_TOOLS)
    print_calls(calls)
    print()

print("  Note Q4: 'the latest build status' names no service. Watch whether")
print("  the model guesses one, asks, or skips the tool.")
print()

# ═══════════════════════════════════════════════════════════════
# Part B — The lever: vague descriptions vs precise descriptions
# ═══════════════════════════════════════════════════════════════
print("  ── Part B: The description lever ───────────────────────────")
print()
print("  Same question, same two tools, same raw data. ONLY the tool")
print("  descriptions change. Routing is a design problem.")
print()
question_b = "Is the payment-api healthy and what was deployed most recently?"

print("  ⏸  PAUSE & PREDICT: the vague set says 'Get service information.' /")
print("     'Get records.' Will it route the same as the precise set?")
pause()
print()

print(f"  Question: {question_b}")
print()
print("  VAGUE descriptions:")
calls_vague = decide_calls(question_b, VAGUE)
print_calls(calls_vague)
print()
print("  PRECISE descriptions:")
calls_precise = decide_calls(question_b, PRECISE)
print_calls(calls_precise)
print()

print(BORDER)
print("  ROUTING IS A DESIGN PROBLEM, NOT A MODEL PROBLEM.")
print("  Above are the OBSERVED calls for each case — they vary run to")
print("  run. The lever you control is not the model; it is each tool's")
print("  name and description. Vague description → vague routing.")
print("  These exact cases are scored in shared/evals/week-04-tool-selection.yaml")
print()
print("  YOUR TURN:")
print("    • Add a THIRD tool whose purpose overlaps tool #2 — does routing")
print("      degrade? When is 'fewer, sharper tools' better than more?")
print("    • Run the same question 5×. How stable is routing at temp 0?")
print(BORDER)
