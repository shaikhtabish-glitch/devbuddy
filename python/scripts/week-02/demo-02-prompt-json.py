"""Demo 2: Prompt JSON + Temperature — Extract to Schema
Give the LLM a JSON schema + input text. Ask it to extract matching data.
At temp=0: clean extraction. At temp=1.0: model adds markdown, invents fields, breaks.
Run: python scripts/week-02/demo-02-prompt-json.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from src.llm import get_llm
from langchain_core.messages import HumanMessage

print("=" * 60)
print("  Demo 2: Extract to Schema — Temperature Breaks Extraction")
print("=" * 60)
print()

diff = """Fix login redirect loop in auth-service (PROJ-421)
Changed session token validation in src/auth.py lines 42-58.
Previously expired tokens caused infinite redirect for 15% of users.
Now returns 401 with clear error. No DB changes. Rollback: revert commit.
Files: src/auth.py, tests/test_auth.py"""

# LOOSENED: No "ONLY JSON" or "No markdown" constraints.
# This lets high temperature naturally introduce conversational filler or markdown.
schema_prompt = """Analyze the following diff and extract the data into a JSON object matching this structure:

{
  "change": {
    "type": "bug" | "feature" | "refactor" | "hotfix",
    "severity": "low" | "medium" | "high" | "critical",
    "ticket": "extract ticket ID from diff, null if none"
  },
  "details": {
    "summary": "one sentence from the diff",
    "root_cause": "what was the underlying issue",
    "user_impact_pct": "extract percentage if mentioned, null if not"
  },
  "technical": {
    "files_changed": ["list exact file paths from diff"],
    "db_changed": true | false,
    "rollback": "how to roll back, from the diff"
  }
}

DIFF:
"""

for temp in [0.0, 0.5, 1.0]:
    llm = get_llm(temperature=temp)
    response = llm.invoke([HumanMessage(content=f"{schema_prompt}\n{diff}")])
    raw = response.content.strip()

    try:
        data = json.loads(raw)
        print(data)
        sev = data["change"]["severity"]
        ticket = data["change"]["ticket"]
        files = data["technical"]["files_changed"]
        print(f"  temp={temp}: ✅ extracted → severity={sev}, ticket={ticket}, files={files}")
    except json.JSONDecodeError:
        preview = raw[:80].replace("\n", " ")
        print(f"  temp={temp}: ❌ Parse failed → {preview}...")
    except (KeyError, TypeError) as e:
        print(f"  temp={temp}: ⚠️ Valid JSON but missing field: {e}")
    print()

print("=" * 60)
print("  temp=0.0  → clean extraction into schema")
print("  temp=1.0  → adds markdown, skips fields, invents keys")
print("  'Extract into this schema' is a request. Pydantic is a contract.")
print("=" * 60)
