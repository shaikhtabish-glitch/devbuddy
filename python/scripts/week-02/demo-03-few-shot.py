"""
Demo 3: Few-shot — the prompt steers the JUDGMENT, the schema fixes the FORMAT.

Same PR. Same schema. Two system prompts:
  - no few-shot: the model applies its default severity rubric.
  - with few-shot: two examples recalibrate that rubric.
The format stays valid (BuildCheck) both times; the judgment (severity) is steered.

Run: python scripts/week-02/demo-03-few-shot.py
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore", message=".*Pydantic serializer.*")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_core.messages import HumanMessage, SystemMessage
from src.llm import get_llm
from src.schemas import BuildCheck

PR_TITLE = "Consolidate error handling across user profile module"
PR_DIFF = (
    "Moved duplicate try/except blocks from 6 profile endpoints into a shared\n"
    "error_handler.py decorator. No behavior changes.\n"
    "Files: src/profiles/error_handler.py, src/profiles/views.py"
)

BASE_PROMPT = (
    "You are a code reviewer. Analyze the given PR and return a BuildCheck.\n"
    "- severity: 'critical' if it touches auth, payments, or security. "
    "'high' if it changes core logic. 'medium' for feature work. 'low' for docs/typos.\n"
    "- summary: one sentence describing what changed and why.\n"
    "- affected_files: list the files mentioned in the diff.\n"
    "- project: extract the project or service name from the PR context."
)

FEW_SHOT_PROMPT = BASE_PROMPT + (
    "\n\nHere are examples to calibrate severity:\n"
    "<example>\n"
    "PR: 'Consolidated error handling into a shared decorator across 6 endpoints'\n"
    "severity: high — it touches the core request path of every endpoint.\n"
    "</example>\n"
    "<example>\n"
    "PR: 'Updated the README with setup steps'\n"
    "severity: low — documentation only.\n"
    "</example>"
)

print("=" * 70)
print("  Demo 3: Few-shot — the prompt steers the JUDGMENT")
print("=" * 70)
print()
print(f"  INPUT (same for both runs): {PR_TITLE}")
print()

llm = get_llm(temperature=0.0)
structured = llm.with_structured_output(BuildCheck)

# ── Run 1: no few-shot ─────────────────────────────────────────
print("-" * 70)
print("  RUN 1: default prompt (no examples)")
print("-" * 70)
print()
r1 = structured.invoke([
    SystemMessage(content=BASE_PROMPT),
    HumanMessage(content=f"PR Title: {PR_TITLE}\n\nDiff:\n{PR_DIFF}"),
])
print(f"    severity = {r1.severity}")
print(f"    summary  = \"{r1.summary}\"")
print()

# ── Run 2: with few-shot ───────────────────────────────────────
print("-" * 70)
print("  RUN 2: same prompt + a few-shot example steering severity up")
print("-" * 70)
print()
r2 = structured.invoke([
    SystemMessage(content=FEW_SHOT_PROMPT),
    HumanMessage(content=f"PR Title: {PR_TITLE}\n\nDiff:\n{PR_DIFF}"),
])
print(f"    severity = {r2.severity}")
print(f"    summary  = \"{r2.summary}\"")
print()

print("  Same input. Same schema. The FORMAT never changed (both are valid")
print("  BuildCheck objects). The JUDGMENT changed: medium → high.")
print()
print("  Key: the schema guarantees the SHAPE; the prompt (few-shot) steers")
print("  the CONTENT. Few-shot for format is redundant once you have a schema —")
print("  but few-shot for judgment steers what the model decides.")
print("=" * 70)
