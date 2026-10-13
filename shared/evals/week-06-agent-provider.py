"""Promptfoo provider that drives the REAL DevBuddy agent (Week 6).

Not a prompt-level eval: each test runs the full LangGraph agent —
planner, registry checks, guards — and returns a compact JSON summary
the YAML asserts against. Structural outcomes only (paths, refusal,
blocking) — never the model's prose.

Prerequisites (see week-06-agent-planning.yaml header):
  OPENROUTER_API_KEY, Qdrant (:6333), MCP server (:8000)

Run:  npx promptfoo@latest eval --config week-06-agent-planning.yaml
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))  # shared/evals → repo root
_PY = os.path.join(_ROOT, "python")
if _PY not in sys.path:
    sys.path.insert(0, _PY)

from src.agent import run_dynamic_agent  # noqa: E402  (path set above)


def _dedupe(steps):
    out = []
    for step in steps:
        if not out or out[-1] != step:
            out.append(step)
    return out


def call_api(prompt, options=None, context=None):
    """Run one query through the real agent; return a JSON summary."""
    query = ((context or {}).get("vars") or {}).get("query") or prompt

    try:
        result = run_dynamic_agent(query)
    except Exception as e:  # a crash is a finding, not a silent pass
        return {"output": json.dumps({"fatal": f"{type(e).__name__}: {e}",
                                      "query": query})}

    report = result.get("report")
    verdict_ready = None
    answer = ""
    if report is not None:
        answer = report.answer
        if report.verdict is not None:
            verdict_ready = report.verdict.ready

    error = result.get("error") or ""
    summary = {
        "query": query,
        "path": _dedupe([m.get("step") for m in result.get("messages", [])]),
        "steps": result.get("steps"),
        "cost": round(result.get("cost", 0.0), 6),
        "error": error,
        "refusal": error.startswith("refused"),
        "blocked": error.startswith("guard"),
        "ready": verdict_ready,
        "answer": answer,
    }
    return {"output": json.dumps(summary)}