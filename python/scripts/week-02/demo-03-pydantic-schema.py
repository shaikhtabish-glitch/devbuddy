"""Demo 3: Pydantic Schema + Temperature
Same PR. Same intent. Now using Pydantic with_structured_output().
Shows: schema constraint guarantees valid output, even at high temperature.
Run: python scripts/week-02/demo-03-pydantic-schema.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.schemas import analyze_pr

print("=" * 60)
print("  Demo 3: Pydantic Schema — Contract, Not Request")
print("=" * 60)
print()

pr = "Fix login redirect loop in auth-service. Changed auth.py line 42-58."

passed = 0
for i in range(3):
    result = analyze_pr("Fix login redirect loop", "Changed auth.py line 42-58.", temperature=0.7)
    passed += 1
    print(f"  Run {i+1}: ✅ BuildCheck(")
    print(f"         project='{result.project}'")
    print(f"         severity='{result.severity}'")
    print(f"         summary='{result.summary[:60]}...'")
    print(f"         affected_files={result.affected_files}")
    print(f"         )")

print()
print(f"  Result: {passed}/3 — always a valid typed object")
print()
print("=" * 60)
print("  Schema is a contract, not a request.")
print("  Prompt JSON = hope. Pydantic = engineering.")
print("=" * 60)
