"""
Demo 2: Dynamic Routing — model decides the steps

Runs the dynamic agent on 3 different queries. The model
decides which steps to execute based on the query content.

Run: python scripts/week-06/demo-02-dynamic-routing.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent import run_dynamic_agent, run_fixed_chain

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
print("  Q1 (health only)    → fewer steps, lower cost")
print("  Q2 (deploys+incidents) → different path, different tools")
print("  Q3 (full assessment) → all steps, highest cost")
print()
print("  Fixed chain:  3 steps every time, ~$X")
print("  Dynamic agent: adapts to the query, $ varies")
print()
print("  Cost comparison: dynamic costs more (routing decisions)")
print("  but adapts to ANY query. Fixed chain costs less but is")
print("  hardcoded to one service and one path.")
print("=" * 70)
