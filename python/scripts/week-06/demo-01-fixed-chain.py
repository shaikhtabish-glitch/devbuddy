"""
Demo 1: Fixed Chain — extract → retrieve → build → report

Runs the fixed 4-step agent. Extracts the service name from the
query, so it checks the RIGHT service. Predictable, auditable,
but rigid — always the same path regardless of query complexity.

Requires: MCP server running (python src/mcp_server.py in another terminal)
Run: python scripts/week-06/demo-01-fixed-chain.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent import run_fixed_chain

print("=" * 70)
print("  Demo 1: Fixed Chain — Extract → Retrieve → Build → Report")
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
print("  Fixed chain: 4 steps every time. Predictable, auditable,")
print("  but rigid. The dynamic agent can adapt — run demo-02 to")
print("  see it add deploys and incidents checks when needed.")
print("=" * 70)
