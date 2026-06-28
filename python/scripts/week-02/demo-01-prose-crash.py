"""Demo 1: Prose → Crash
Shows why free-text LLM responses break pipelines.
Run: python scripts/week-02/demo-01-prose-crash.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from src.llm import get_llm
from langchain_core.messages import HumanMessage

print("=" * 60)
print("  Demo 1: Prose → Crash")
print("=" * 60)
print()

llm = get_llm(temperature=0)

# Ask for analysis — get prose back
response = llm.invoke([HumanMessage(content=(
    "Analyze this PR. What is the severity? "
    "PR: Fix login bug. Changed auth.py line 42."
))])

print("RAW OUTPUT:")
print(f"  {response.content[:300]}")
print()

# Try to parse as JSON — will crash
print("PARSING AS JSON:")
try:
    json.loads(response.content)
    print("  ✅ Parsed successfully (unlikely with prose)")
except json.JSONDecodeError as e:
    print(f"  💥 CRASH: {e}")
    print()
    print("  This is CODE SLOP.")
    print("  Free-text responses break pipelines.")
    print("  The fix: structured output with a schema.")

print()
print("=" * 60)
print("  Next: Demo 2 — python scripts/demo-02-schema-success.py")
print("=" * 60)
