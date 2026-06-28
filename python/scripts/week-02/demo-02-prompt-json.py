"""Demo 2: Prompt JSON + Temperature — Schema Degrades
Same PR. Asked for JSON in the prompt. Vary temperature.
At temp=0: clean JSON. At temp=1.0: model drifts, adds text, breaks format.
Run: python scripts/week-02/demo-02-prompt-json.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from src.llm import get_llm
from langchain_core.messages import HumanMessage

print("=" * 60)
print("  Demo 2: Prompt JSON — Temperature Breaks the Format")
print("=" * 60)
print()

pr = "Fix login redirect loop in auth-service. Changed auth.py line 42-58."
prompt = (
    'Return ONLY valid JSON. No other text.\n'
    '{"severity": "low/medium/high/critical", "summary": "one sentence"}\n\n'
    f'PR: {pr}'
)

for temp in [0.0, 0.5, 1.0]:
    llm = get_llm(temperature=temp)
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip()
    try:
        data = json.loads(raw)
        print(f"  temp={temp}: ✅ Valid JSON  → severity={data.get('severity','?')}")
    except json.JSONDecodeError:
        preview = raw[:80].replace("\n", " ")
        print(f"  temp={temp}: ❌ Parse failed → {preview}...")
    print()

print("=" * 60)
print("  temp=0.0  → model follows instructions strictly")
print("  temp=1.0  → model gets creative, adds text, breaks JSON")
print("  'Return JSON' is a hope, not a contract.")
print("=" * 60)
