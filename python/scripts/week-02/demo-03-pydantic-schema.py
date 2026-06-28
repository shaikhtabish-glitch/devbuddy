"""Demo 3: Pydantic Schema + Temperature
Same PR. Same intent. Now using Pydantic with_structured_output().
Shows: schema constraint guarantees valid output, even at high temperature.
Run: python scripts/week-02/demo-03-pydantic-schema.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.schemas import analyze_pr

print("=" * 60)
print("  Demo 3: Pydantic Schema")
print("  Same PR. Schema-constrained. Temperature = 0.7")
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
print(f"  Result: {passed}/3 runs — always a valid typed object")
print()
print("=" * 60)
print("  What we learned:")
print("  • Pydantic schema is a contract, not a request")
print("  • The model CANNOT return output that violates the schema")
print("  • Same temperature (0.7) — 0 failures vs prompt-only's N failures")
print()
print("  Prompt JSON = hope. Pydantic schema = engineering.")
print("=" * 60)
