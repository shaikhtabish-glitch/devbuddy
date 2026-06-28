"""Demo 2: Prompt JSON + Temperature — Complex Schema Degrades
Complex JSON schema in the prompt. At temp=0: clean. At temp=1.0: model drifts.
Run: python scripts/week-02/demo-02-prompt-json.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from src.llm import get_llm
from langchain_core.messages import HumanMessage

print("=" * 60)
print("  Demo 2: Prompt JSON — Complex Schema, Temperature Breaks It")
print("=" * 60)
print()

pr = "Fix login redirect loop in auth-service. Changed auth.py line 42-58."
prompt = (
    'Return ONLY valid JSON. No markdown, no explanation, no other text.\n'
    '{\n'
    '  "analysis": {\n'
    '    "severity": "low" | "medium" | "high" | "critical",\n'
    '    "confidence": 0.0 to 1.0,\n'
    '    "category": "bug" | "feature" | "refactor" | "docs"\n'
    '  },\n'
    '  "impact": {\n'
    '    "services_affected": ["list of service names"],\n'
    '    "user_facing": true | false,\n'
    '    "rollback_risk": "none" | "low" | "medium" | "high"\n'
    '  },\n'
    '  "files": ["exact file paths from the diff"],\n'
    '  "reviewer_notes": "one sentence"\n'
    '}\n\n'
    f'PR: {pr}'
)

for temp in [0.0, 0.5, 1.0]:
    llm = get_llm(temperature=temp)
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip()
    try:
        data = json.loads(raw)
        sev = data["analysis"]["severity"]
        files = data.get("files", [])
        print(f"  temp={temp}: ✅ severity={sev}, files={files}")
    except (json.JSONDecodeError, KeyError) as e:
        preview = raw[:80].replace("\n", " ")
        print(f"  temp={temp}: ❌ {type(e).__name__} → {preview}...")
    print()

print("=" * 60)
print("  temp=0.0  → model follows the complex schema strictly")
print("  temp=1.0  → model gets creative, misses fields, adds markdown")
print("  Complex prompts break. Schema constraints don't.")
print("=" * 60)
