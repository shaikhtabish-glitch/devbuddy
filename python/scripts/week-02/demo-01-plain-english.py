"""Demo 1: Plain English Prompt + Temperature
Ask the model something with no single correct answer. Vary temperature.
Run: python scripts/week-02/demo-01-plain-english.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.llm import get_llm
from langchain_core.messages import HumanMessage

print("=" * 60)
print("  Demo 1: Temperature Changes Everything")
print("  Same prompt. Same model. Different temperatures.")
print("=" * 60)
print()

for temp in [0.0, 0.5, 1.0]:
    llm = get_llm(temperature=temp)
    response = llm.invoke([HumanMessage(content="Name a color and a number. One line only.")])
    print(f"  temp={temp}: {response.content.strip()}")
    print()

print("=" * 60)
print("  Same prompt. Different answers. No contract. No structure.")
print("  This is what you get without schema constraints.")
print("=" * 60)
