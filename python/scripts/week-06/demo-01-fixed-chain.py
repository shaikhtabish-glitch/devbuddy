"""
Demo 1: Fixed Chain — extract → retrieve → build → report

Runs the fixed 4-step agent and traces every step so you can
see exactly what the chain does. No black box — every step,
its input, and its output are shown.

Requires: MCP server running (python src/mcp_server.py in another terminal)
Run: python scripts/week-06/demo-01-fixed-chain.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from src.llm import get_llm
from src.agent import (
    extract_service, retrieve_context, check_build,
    generate_report, AgentState, _init_state, _call_mcp_tool,
)

print()
print("=" * 65)
print("  Demo 1: Fixed Chain — Trace Every Step")
print("=" * 65)
print()
print("  A fixed chain is a PREDEFINED sequence of steps.")
print("  The path never changes regardless of the query.")
print("  Each step is traced below so you can see the flow.")
print()


def trace_fixed_chain(query: str):
    """Run the fixed chain step-by-step with tracing."""

    state = _init_state(query)
    print(f"  📥  QUERY: \"{query}\"")
    print(f"  {'─' * 59}")

    # Step 1: Extract service
    print(f"  [1/4]  EXTRACT  — Which service is the query about?")
    state = extract_service(state)
    print(f"          →  service = {state['service_name']}")
    print()

    # Step 2: Retrieve context
    print(f"  [2/4]  RETRIEVE  — Search docs for relevant context")
    state = retrieve_context(state)
    context_preview = state["context"][:120].replace("\n", " ")
    print(f"          →  {context_preview}...")
    print()

    # Step 3: Check build
    print(f"  [3/4]  BUILD  — Call get_build_status({state['service_name']})")
    state = check_build(state)
    try:
        bs = json.loads(state["build_status"])
        print(f"          →  status = {bs.get('status', '?').upper()}")
        print(f"          →  last deploy = {bs.get('last_deploy', '?')}")
    except json.JSONDecodeError:
        print(f"          →  {state['build_status'][:100]}")
    print()

    # Step 4: Generate report
    print(f"  [4/4]  REPORT  — Synthesize findings into a report")
    state = generate_report(state)
    print(f"          →  cost = ${state['cost']:.6f}")
    print()

    print(f"  {'─' * 59}")
    print(f"  📤  REPORT:")
    print(f"  {state['report']}")
    print()


# ── Run two queries ────────────────────────────────────────────

trace_fixed_chain("Is the payment-api ready for v2.1?")
trace_fixed_chain("Is the auth-service ready for release?")

print("=" * 65)
print("  Fixed chain: 4 steps. Same sequence every time.")
print("  🔀  Path:  📄 docs → 🏗️ build → 📝 report")
print("  Predictable and auditable, but can't add steps like")
print("  deploys or incidents. Run demo-02 for dynamic routing.")
print("=" * 65)
print()
