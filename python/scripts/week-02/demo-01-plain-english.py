"""Demo 1: Plain English — No JSON, Temperature Drift
Same prompt. No schema. Vary temp. Watch output change completely.
Run: python scripts/week-02/demo-01-plain-english.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.llm import get_llm
from langchain_core.messages import HumanMessage

print("=" * 60)
print("  Demo 1: Plain English — No Schema, Temperature Drift")
print("=" * 60)
print()

pr = "Fix login redirect loop in auth-service. Changed auth.py line 42-58."

for temp in [0.0, 0.5, 1.0]:
    llm = get_llm(temperature=temp)
    response = llm.invoke([HumanMessage(content=f"Summarize: {pr}")])
    print(f"  temp={temp}:")
    print(f"    {response.content.strip()[:100]}")
    print()

print("=" * 60)
print("  temp=0.0  → same answer every time. Predictable. Boring.")
print("  temp=1.0  → different answer every time. Creative. Unreliable.")
print("  No contract means no pipeline.")
print("=" * 60)
