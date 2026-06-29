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
print("  Query 1: about payment-api → checks payment-api ✅")
print("  Query 2: about auth-service → checks payment-api ❌")
print()
print("  Query 2 asked about AUTH-SERVICE. But the chain hardcodes")
print("  get_build_status('payment-api'). The build status in the")
print("  report says 'service: payment-api, status: degraded' —")
print("  that's the WRONG service. The report looks plausible but")
print("  the data is silently corrupted. Fixed chains can't adapt.")
print()
print("  Fixed chains are predictable but brittle.")
print("=" * 70)
