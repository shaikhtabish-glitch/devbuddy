"""Demo 1: Plain English Prompt
Same PR. One sentence please. Vary temperature. Watch output drift.
Run: python scripts/week-02/demo-01-plain-english.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.llm import get_llm
from langchain_core.messages import HumanMessage

print("=" * 60)
print("  Demo 1: Plain English — No JSON, Just Prose")
print("=" * 60)
print()

pr = "PR: Fix login redirect loop in auth-service. Changed auth.py line 42-58."

for temp in [0.0, 0.5, 1.0]:
    llm = get_llm(temperature=temp)
    response = llm.invoke([HumanMessage(content=f"In one sentence, what does this PR do? {pr}")])
    print(f"  temp={temp}: {response.content.strip()}")
    print()

print("=" * 60)
print("  Prose is unpredictable. Temperature changes everything.")
print("  You cannot build a pipeline on this.")
print("=" * 60)
