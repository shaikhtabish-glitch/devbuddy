"""
Demo 2: Dynamic Routing — model decides the steps

Runs the dynamic agent on 3 different queries. Shows which steps
the model chose for each query, so you can compare routing decisions.

Requires: MCP server running (python src/mcp_server.py in another terminal)
Run: python scripts/week-06/demo-02-dynamic-routing.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent import run_dynamic_agent

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

    # Show which data was collected
    collected = []
    if result.get("context"):   collected.append("📄 docs")
    if result.get("build_status"): collected.append("🏗️  build")
    if result.get("deploys"):   collected.append("🚀 deploys")
    if result.get("incidents"): collected.append("🚨 incidents")

    print(f"  ⚡  Steps: {result['steps']}  |  Cost: ${result['cost']:.6f}")
    print(f"  📊  Collected: {' + '.join(collected) if collected else '(none)'}")
    print(f"  {'─' * 59}")
    print(f"  {result['report'][:300]}")
    print()

print("=" * 65)
print("  Dynamic agent adapts — more steps = higher cost,")
print("  but greater correctness. Fixed chain (demo-01) is")
print("  cheaper but always runs docs + build regardless.")
print("=" * 65)
print()
