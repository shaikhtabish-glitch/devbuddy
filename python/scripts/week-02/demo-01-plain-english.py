"""Demo 1: Plain English Prompt + Temperature
Same PR. Plain English — no JSON requested. Vary temperature. Watch output drift.
Run: python scripts/week-02/demo-01-plain-english.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.llm import get_llm
from langchain_core.messages import HumanMessage

print("=" * 60)
print("  Demo 1: Plain English Prompt")
print("  Same PR. No JSON. Just prose.")
print("=" * 60)
print()

pr = "Fix login redirect loop in auth-service. Changed auth.py line 42-58."

for temp in [0.0, 0.5, 1.0]:
    llm = get_llm(temperature=temp)
    response = llm.invoke([HumanMessage(content=f"Analyze this PR: {pr}")])
    print(f"  temp={temp}:")
    print(f"    {response.content[:120]}...")
    print()

print("=" * 60)
print("  What we learned:")
print("  • Output is prose — unpredictable, unparseable")
print("  • Temperature changes the answer — same input, different result")
print("  • You cannot build a pipeline on this")
print("=" * 60)
