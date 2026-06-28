"""Demo 2: Prompt with JSON Instructions + Temperature
Same PR. Asked for JSON in the prompt. Runs 3 times at temp=0.7.
Shows: even with explicit JSON instructions, the model sometimes fails.
Run: python scripts/week-02/demo-02-prompt-json.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from src.llm import get_llm
from langchain_core.messages import HumanMessage

print("=" * 60)
print("  Demo 2: Prompt with JSON Instructions")
print("  Same PR. Asked for JSON. Temperature = 0.7")
print("=" * 60)
print()

llm = get_llm(temperature=0.7)
pr = "Fix login redirect loop in auth-service. Changed auth.py line 42-58."

prompt = (
    "Analyze this PR. Return ONLY valid JSON with these fields:\n"
    '{"severity": "low/medium/high/critical", "summary": "one sentence"}\n\n'
    f"PR: {pr}"
)

passed = 0
for i in range(3):
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content
    try:
        data = json.loads(raw)
        print(f"  Run {i+1}: ✅ Valid JSON — severity={data.get('severity', '?')}")
        passed += 1
    except json.JSONDecodeError as e:
        print(f"  Run {i+1}: ❌ Parse failed — {e.msg} (line {e.lineno})")
        if raw.startswith("```"):
            print(f"         Model wrapped output in markdown block")
        elif raw[:1] not in ("{", "["):
            print(f"         Model added text before the JSON: {raw[:80]}...")
        print()

print(f"  Result: {passed}/3 runs produced valid JSON")
print()
print("=" * 60)
print("  What we learned:")
print("  • 'Return JSON' in the prompt is a request, not a guarantee")
print("  • At temperature=0.7, the model sometimes ignores the request")
print("  • This is hope-based architecture — it works until it doesn't")
print("=" * 60)
