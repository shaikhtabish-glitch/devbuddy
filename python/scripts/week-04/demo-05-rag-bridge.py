"""
Demo 5: RAG as a Tool — the composition pattern

THE POINT OF THIS DEMO: a tool is just data with a name. The model does
not care whether the data came from a hardcoded dict or your Week-3
vector store. Where data comes from is an implementation detail.

This tool calls src.rag.retrieve() (the Week-3 pipeline) and asks the LLM
to extract an answer from the retrieved chunks — wrapped as a normal tool
the model can route to.

Run: python scripts/week-04/demo-05-rag-bridge.py      (needs Qdrant running)
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage

from src.rag import index_documents, retrieve
from src.tools import execute_tool_safely
from src.llm import get_llm

BORDER = "=" * 70

# Ensure the Week-3 index exists before the demo tool runs.
index_documents(chunk_size=512, chunk_overlap=64)

print(BORDER)
print("  Demo 5: RAG as a Tool — a tool is just data with a name")
print(BORDER)
print()

# ── Define the tool ────────────────────────────────────────────
# The interface is identical to get_build_status: name, args, JSON return.
# The DATA SOURCE is different — Week 3's vector store, not a dict.


def _rag_build_status(service_name: str) -> str:
    chunks = retrieve(f"{service_name} build status health deploy", k=5)
    if not chunks:
        return json.dumps({"status": "unknown", "error": f"No docs for '{service_name}'"})

    context = "\n\n".join(chunks)
    llm = get_llm(temperature=0.0)
    response = llm.invoke([
        SystemMessage(content=(
            "Extract the build/health status from the context. Return JSON with "
            "'status' (healthy/degraded/down/unknown) and 'last_deploy' (timestamp). "
            "Only use data from the context."
        )),
        HumanMessage(content=f"Service: {service_name}\n\nContext:\n{context}"),
    ])
    text = response.content.strip()
    # The model may wrap JSON in prose — try to salvage a JSON object.
    try:
        return json.dumps(json.loads(text))
    except Exception:
        return text


@tool
def get_build_status_from_docs(service_name: str) -> str:
    """Return the build/health status of a service by searching our knowledge base."""
    return _rag_build_status(service_name)


print("  The tool:")
print("    get_build_status_from_docs(service_name)  →  status JSON")
print("    data source: retrieve() from src.rag (Week 3) + LLM extraction")
print()
print("  Compare with src.tools.get_build_status — SAME interface, different")
print("  data source. Nothing else in the stack changed.")
print()

# ── Use it through the app layer, like any other tool ──────────
tool_call = {"name": "get_build_status_from_docs", "args": {"service_name": "payment-api"}}
print("  ⏸  PAUSE & PREDICT: our mock dict had payment-api as 'degraded'.")
print("     What will the DOCS say? Predict, then continue.")
try:
    input("  ⏸  Press Enter to run the tool… ")
except EOFError:
    print()
print()

registry = {"get_build_status_from_docs": get_build_status_from_docs}
result = execute_tool_safely(tool_call, tools_by_name=registry)
print(f"  Tool returned: {result}")
print()

print(BORDER)
print("  THE COMPOSITION PATTERN: the orchestrator (Week 6) does not care")
print("  whether a tool's data comes from a dict, an API, or a vector store.")
print("  A tool is a contract: name + args + JSON out. Source is a detail.")
print()
print("  YOUR TURN:")
print("    • Point get_recent_deploys from docs too — same pattern.")
print("    • Add a 'min_score' guard inside the tool so a weak retrieval")
print("      returns a structured 'no match', not a guess.")
print(BORDER)
