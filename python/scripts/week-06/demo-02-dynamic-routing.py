"""
Demo 2: Dynamic Routing — the model PROPOSES, the registry disposes

Runs the dynamic agent on 3 queries and prints, for every planning
decision: what the model proposed, what the code accepted/rejected, and
why. That proposal→decision stream — not the step list — is the lesson.

Also measures fixed vs dynamic on the same query (steps + cost).

Requires: MCP server (python src/mcp_server.py) + Qdrant (docker-compose up -d)
Run: python scripts/week-06/demo-02-dynamic-routing.py
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent import run_dynamic_agent, run_fixed_chain, format_report


def show_plans(result) -> None:
    """Print every plan event: proposal → decision (reason)."""
    plans = [m for m in result["messages"] if m["step"] == "plan"]
    if not plans:
        return
    print("      🧠  plan decisions (LLM proposes → code disposes):")
    for p in plans:
        proposal = p.get("proposal", "—")
        decision = p.get("decision", "?")
        cost = f"  · ${p.get('cost', 0):.6f}" if p.get("cost") else ""
        marker = "✅" if decision == "accept" else "⚠️ "
        detail = ""
        if "corrected_to" in p and p["corrected_to"] != p.get("proposal"):
            detail = f"  → dispatched: {p['corrected_to']}"
        reason = f"  ({p['reason']})" if "reason" in p else ""
        print(f"         {marker} proposed {proposal} → {decision}{reason}"
              f"{detail}{cost}")


print()
print("=" * 65)
print("  Demo 2: Dynamic Routing — LLM proposes, registry disposes")
print("=" * 65)
print()
print("  The graph's ROUTES are still static; which route is taken at")
print("  runtime comes from a planning node. The model may only propose")
print("  steps the registry allows for this query's category — watch the")
print("  decisions below: accepted, corrected, or handed to the guard.")
print()

queries = [
    ("Is the payment-api healthy?",                     "health only"),
    ("What was deployed recently for payment-api and are there any incidents?",
     "multi-intent (deploys + incidents)"),
    ("Give me a full readiness assessment for payment-api.", "full assessment"),
]

for i, (query, label) in enumerate(queries):
    print(f"  ── {label} ──")
    print(f"  📥  QUERY: \"{query}\"")
    result = run_dynamic_agent(query)
    time.sleep(1)  # let SSE connection close cleanly before next query

    # The path is what the agent RECORDED — an audit trail, not a guess.
    path = [m["step"] for m in result["messages"]]

    print(f"  ⚡  Steps: {result['steps']}  |  Cost: ${result['cost']:.6f}")
    print(f"  🔀  Path:   {' → '.join(path)}")
    show_plans(result)
    if result["error"]:
        print(f"  ⚠️   Error:  {result['error']}")
    print(f"  {'─' * 59}")
    print(format_report(result["report"]))
    print()

    # ── Measured comparison: same query through the fixed chain ──
    if i == 0:
        print("  📊  SAME query through demo-01's fixed chain:")
        fixed = run_fixed_chain(query)
        time.sleep(1)
        print(f"      fixed   : {fixed['steps']} steps · ${fixed['cost']:.6f}")
        print(f"      dynamic : {result['steps']} steps · ${result['cost']:.6f}")
        print(f"      → dynamic pays for planning LLM calls; fixed pays for")
        print(f"        running its steps whether you needed them or not.")
        print()

print("=" * 65)
print("  What varied between the three queries? Not the graph — the")
print("  PLAN decisions. Same nodes, same edges, different runtime path,")
print("  different cost. Measure your own: take-home Part A runs 5")
print("  queries through both and compares.")
print("=" * 65)
print()