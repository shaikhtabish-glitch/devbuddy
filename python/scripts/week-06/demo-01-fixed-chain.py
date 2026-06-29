"""
Demo 1: Fixed Chain — retrieve → build → report

Runs the fixed 3-step agent. Predictable, auditable, but
always checks payment-api regardless of the query.

Run: python scripts/week-06/demo-01-fixed-chain.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent import run_fixed_chain

print("=" * 70)
print("  Demo 1: Fixed Chain — Retrieve → Build → Report")
print("=" * 70)
print()

queries = [
    "Is the payment-api ready for v2.1?",
    "Is the auth-service ready for release?",
]

for query in queries:
    print(f"  Query: {query}")
    result = run_fixed_chain(query)
    print(f"  Steps taken: {result['steps']}")
    print(f"  Cost: ~${result['cost']:.6f}")
    print()
    print(f"  Report:")
    print(f"  {result['report'][:500]}")
    print()

print("=" * 70)
print("  Fixed chain: extract service → retrieve → build → report")
print("  4 steps every time. Predictable path. But the tools still")
print("  use the extracted service name — so Query 1 and Query 2")
print("  both check the RIGHT service now. The chain is correct")
print("  but still rigid. Add a new tool and the chain can't use it.")
print()
print("  Dynamic agent has the same 4 steps but can add more.")
print("=" * 70)
