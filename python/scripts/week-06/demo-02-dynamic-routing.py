"""
Demo 2: Dynamic Routing — model decides the steps

Runs the dynamic agent on 3 different queries. The model
decides which steps to execute based on the query content.

Run: python scripts/week-06/demo-02-dynamic-routing.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent import run_dynamic_agent

print("=" * 70)
print("  Demo 2: Dynamic Routing — Model Decides the Steps")
print("=" * 70)
print()

queries = [
    "Is the payment-api healthy?",
    "What was deployed recently for payment-api and are there any incidents?",
    "Give me a full readiness assessment for payment-api.",
]

for query in queries:
    print(f"  Query: {query}")
    result = run_dynamic_agent(query)
    print(f"  Steps taken: {result['steps']}")
    print(f"  Cost: ~${result['cost']:.6f}")
    print()
    print(f"  Report:")
    print(f"  {result['report'][:400]}")
    print()

print("=" * 70)
print("  Q1 (health only)       → retrieve + build + report")
print("  Q2 (deploys + incidents) → retrieve + deploys + incidents + report")
print("  Q3 (full assessment)    → all 4 data steps + report")
print()
print("  Dynamic agent adapts — more steps = higher cost but")
print("  greater correctness. Fixed chain (demo-01) is cheaper")
print("  but always runs the same path regardless of query.")
print()
print("  The tradeoff: cost vs correctness.")
print("=" * 70)
