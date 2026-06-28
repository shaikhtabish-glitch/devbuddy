"""Demo 2: Schema → Success
Same PR. Same model. Now with Pydantic schema — returns typed object.
Run: python scripts/week-02/demo-02-schema-success.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.schemas import analyze_pr

print("=" * 60)
print("  Demo 2: Schema → Success")
print("=" * 60)
print()

result = analyze_pr("Fix login bug", "changed auth.py line 42")

print(f"  Type:       {type(result).__name__} ← typed object, not a string!")
print(f"  Project:    {result.project}")
print(f"  Severity:   {result.severity}")
print(f"  Summary:    {result.summary}")
print(f"  Files:      {result.affected_files}")
print()
print("  ✅ Schema-constrained generation.")
print("  The LLM is now a typed function: input → BuildCheck")
print("  Your code imports it directly. No regex. No json.loads(). No hoping.")

print()
print("=" * 60)
print("  Next: Demo 3 — python scripts/demo-03-side-by-side.py")
print("=" * 60)
