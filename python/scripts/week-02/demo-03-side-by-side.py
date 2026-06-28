"""Demo 3: Side-by-Side — Prompt-Only JSON vs Pydantic Schema
3 runs each at temperature=0.7. Which approach survives?
Run: python scripts/week-02/demo-03-side-by-side.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from src.llm import get_llm
from src.schemas import analyze_pr
from langchain_core.messages import HumanMessage

print("=" * 60)
print("  Demo 3: Prompt-Only JSON vs Pydantic Schema")
print("  Temperature: 0.7 — realistic, not 0")
print("=" * 60)
print()

llm = get_llm(temperature=0.7)
prompt = (
    'Analyze this PR. Return ONLY valid JSON:\n'
    '{"severity": "low/medium/high/critical", "summary": "..."}\n\n'
    'PR: Fix login bug. Changed auth.py line 42.'
)

# ─── Approach A: Prompt-only JSON ───
print("─── Prompt-Only JSON ───")
prompt_pass = 0
for i in range(3):
    response = llm.invoke([HumanMessage(content=prompt)])
    try:
        data = json.loads(response.content)
        print(f"  Run {i+1}: ✅ {data}")
        prompt_pass += 1
    except json.JSONDecodeError:
        print(f"  Run {i+1}: ❌ Parse failed → {response.content[:60]}...")
print(f"  Result: {prompt_pass}/3 passed")
print()

# ─── Approach B: Pydantic Schema ───
print("─── Pydantic Schema ───")
schema_pass = 0
for i in range(3):
    result = analyze_pr("Fix login bug", "changed auth.py line 42", temperature=0.7)
    print(f"  Run {i+1}: ✅ BuildCheck(severity='{result.severity}')")
    schema_pass += 1
print(f"  Result: {schema_pass}/3 passed")
print()

# ─── Verdict ───
print("=" * 60)
if prompt_pass < 3:
    print(f"  Prompt-only: {prompt_pass}/3 — hope-based architecture")
else:
    print(f"  Prompt-only: {prompt_pass}/3 — lucky this time")
print(f"  Pydantic:    {schema_pass}/3 — engineering decision")
print()
print("  One survives production. The other survives until it doesn't.")
print("=" * 60)
print()
print("  Next: Demo 4 — python scripts/demo-04-temperature-drill.py")
print("=" * 60)
