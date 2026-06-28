"""Demo 4: Temperature Drill
Same PR at different temperatures. Watch the output drift.
Run: python scripts/week-02/demo-04-temperature-drill.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.schemas import analyze_pr

print("=" * 60)
print("  Demo 4: Temperature Drill")
print("  Same PR. Same schema. Different temperatures.")
print("=" * 60)
print()

diff = "changed auth.py line 42"

for temp in [0.0, 0.3, 0.7, 1.0]:
    r = analyze_pr("Fix login bug", diff, temperature=temp)
    print(f"  temp={temp}:")
    print(f"    severity: {r.severity}")
    print(f"    summary:  {r.summary[:80]}...")
    print()

print("=" * 60)
print("  Key takeaway:")
print("  temperature=0   → production structured output")
print("  temperature>0   → creative tasks, exploration")
print("  Higher temps    → output may drift, may break schema")
print("=" * 60)
