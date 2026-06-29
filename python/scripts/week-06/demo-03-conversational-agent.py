"""
Demo 3: Conversational Agent — talk to DevBuddy

Type queries. The dynamic agent plans, calls tools, and responds.
Type 'quit' to exit, 'cost' to see cumulative spending.

Run: python scripts/week-06/demo-03-conversational-agent.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent import run_dynamic_agent

print("=" * 70)
print("  DevBuddy Agent — Conversational Mode")
print("=" * 70)
print()
print("  I can check build status, deployment history, active")
print("  incidents, and retrieve documentation. Ask me anything")
print("  about auth-service, payment-api, or inventory-service.")
print()
print("  Commands:  quit  |  cost  |  help")
print()

total_cost = 0.0
turn = 0

while True:
    try:
        query = input("  You → ").strip()
    except (EOFError, KeyboardInterrupt):
        break

    if not query:
        continue
    if query.lower() in ("quit", "exit", "q"):
        break
    if query.lower() == "cost":
        print(f"  💰 Total cost this session: ~${total_cost:.6f}")
        print()
        continue
    if query.lower() == "help":
        print("  Try: 'Is payment-api healthy?'")
        print("       'What was deployed recently for auth-service?'")
        print("       'Any incidents for inventory-service?'")
        print("       'Give me a full readiness report for payment-api'")
        print()
        continue

    turn += 1
    print(f"  ⏳ Turn {turn} — planning and executing...")
    result = run_dynamic_agent(query)
    total_cost += result.get("cost", 0)

    print(f"  Steps: {result['steps']}  |  Cost: ~${result['cost']:.6f}")
    print(f"  ─────────────────────────────────────────────")
    print(f"  {result['report']}")
    print()

print()
print(f"  Session ended. {turn} queries, total cost ~${total_cost:.6f}")
print("=" * 70)
