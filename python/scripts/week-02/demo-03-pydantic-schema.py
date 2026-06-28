"""Demo 3: Pydantic Schema + Temperature — Schema Survives
Same PR. Same temperatures. Pydantic schema. Always valid.
Run: python scripts/week-02/demo-03-pydantic-schema.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.schemas import analyze_pr

print("=" * 60)
print("  Demo 3: Pydantic Schema — Temperature Can't Break It")
print("=" * 60)
print()

pr_text = "Fix login redirect loop in auth-service. Changed auth.py line 42-58."

for temp in [0.0, 0.5, 1.0]:
    result = analyze_pr("Fix login redirect loop", pr_text, temperature=temp)
    print(f"  temp={temp}: ✅ BuildCheck(")
    print(f"    project='{result.project}'")
    print(f"    severity='{result.severity}'")
    print(f"    summary='{result.summary[:60]}...'")
    print(f"    affected_files={result.affected_files}")
    print(f"  )")
    print()

print("=" * 60)
print("  temp=0.0  → valid typed object")
print("  temp=1.0  → valid typed object (content may vary, format never breaks)")
print("  Schema is a contract. Pydantic = engineering.")
print("=" * 60)
