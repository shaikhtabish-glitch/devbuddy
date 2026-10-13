"""
Demo 2: Dynamic Routing — model decides the steps

Runs the dynamic agent on 3 different queries. Shows which steps
the model chose for each query, so you can compare routing decisions.

Requires: MCP server running (python src/mcp_server.py in another terminal)
Run: python scripts/week-06/demo-02-dynamic-routing.py
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent import run_dynamic_agent, format_report

print()
print("=" * 65)
print("  Demo 2: Dynamic Routing — Model Decides the Steps")
print("=" * 65)
print()
print("  A dynamic agent lets the MODEL decide which steps to run.")
print("  Each query below triggers a DIFFERENT set of steps.")
print("  Compare with demo-01: same 4 steps every time vs. adaptive.")
print()

queries = [
    ("Is the payment-api healthy?",                     "health only"),
    ("What was deployed recently for payment-api and are there any incidents?", "deploys + incidents"),
    ("Give me a full readiness assessment for payment-api.", "full assessment"),
]

for query, label in queries:
    print(f"  ── {label} ──")
    print(f"  📥  QUERY: \"{query}\"")
    result = run_dynamic_agent(query)
    time.sleep(1)  # let SSE connection close cleanly before next query

    # The path is what the agent RECORDED — an audit trail, not a guess.
    path = [m["step"] for m in result["messages"]]

    print(f"  ⚡  Steps: {result['steps']}  |  Cost: ${result['cost']:.6f}")
    print(f"  🔀  Path:   {' → '.join(path)}")
    if result["error"]:
        print(f"  ⚠️   Error:  {result['error']}")
    print(f"  {'─' * 59}")
    print(format_report(result["report"]))
    print()

print("=" * 65)
print("  Dynamic agent adapts — more steps = higher cost,")
print("  but greater correctness. Fixed chain is cheaper but")
print("  always runs: 📄 docs → 🏗️ build → 📝 report")
print("=" * 65)
print()
