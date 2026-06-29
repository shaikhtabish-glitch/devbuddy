"""
Week 5 — MCP Server: Shared Tool Ecosystem

Exposes tools over the Model Context Protocol.
Tools retrieve data from Qdrant and synthesize with an LLM.
Write once. Any MCP client in any language can consume them.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

from src.rag import retrieve, hybrid_search
from src.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

mcp = FastMCP(
    name="devbuddy-mcp",
    instructions="DevBuddy MCP Server — build status, deployments, incidents, docs.",
)


# ── Shared synthesis helper ───────────────────────────────────

def _synthesize(query_type: str, service_name: str, chunks: list[str]) -> str:
    """Feed retrieved chunks to LLM, synthesize concise JSON."""
    context = "\n\n---\n\n".join(chunks) if chunks else "(no data found)"
    llm = get_llm(temperature=0)

    prompts = {
        "build/health": (
            "Extract current build/health status. JSON with 'status' "
            "(healthy/degraded/down/unknown) and 'last_deploy' (ISO). "
            "Use the MOST RECENT deploy. Success=healthy, rolling_back/failed=degraded."
        ),
        "deployments": (
            "Extract deployment history. JSON array of {service, version, date, sha, author, status}. "
            "Status: success/failed/rolling_back."
        ),
        "incidents": (
            "Extract active (unresolved) incidents. JSON array of {id, severity, date, summary, status}. "
            "Skip 'Resolved'. Only include 'investigating' or blank status."
        ),
        "docs": (
            "Extract relevant documentation. JSON with 'endpoints' (array of paths), "
            "'error_codes' (array of {code, meaning}), 'sla' (string), 'owner' (string)."
        ),
    }

    response = llm.invoke([
        SystemMessage(content=(
            f"{prompts.get(query_type, 'Extract requested info.')}\n\n"
            "RULES: Only use provided chunks. No invention. "
            "If no data: {\"status\": \"unknown\"}. "
            "Return ONLY valid JSON, no markdown."
        )),
        HumanMessage(content=f"Service: {service_name}\n\nChunks:\n{context}"),
    ])
    return response.content.strip()


# ── Tools ─────────────────────────────────────────────────────

@mcp.tool()
def get_build_status(service_name: str) -> str:
    """Current build/health status for a service. Returns JSON with status and last_deploy."""
    chunks = retrieve(f"{service_name} deployment success failed rolling_back", k=4)
    return _synthesize("build/health", service_name, chunks)


@mcp.tool()
def get_recent_deploys(service_name: str, limit: int = 5) -> str:
    """Last N deployments for a service. JSON array of {version, date, sha, author, status}."""
    chunks = hybrid_search(f"{service_name} deploy SHA author timestamp status", k=4)
    raw = _synthesize("deployments", service_name, chunks)
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            data = data[:limit]
        return json.dumps(data, indent=2)
    except json.JSONDecodeError:
        return raw


@mcp.tool()
def get_active_incidents(service_name: str) -> str:
    """Active (unresolved) incidents for a service. JSON array of {id, severity, date, summary}."""
    chunks = hybrid_search(f"{service_name} INC- Sev severity investigating unresolved", k=4)
    return _synthesize("incidents", service_name, chunks)


@mcp.tool()
def get_service_docs(service_name: str) -> str:
    """Relevant documentation for a service from Qdrant. JSON with endpoints, error_codes, sla, owner."""
    chunks = retrieve(f"{service_name} API specification endpoints error codes SLA owner", k=4)
    return _synthesize("docs", service_name, chunks)


# ── Start up ──────────────────────────────────────────────────

# Ensure Qdrant index exists (skip if already indexed)
try:
    retrieve("ping", k=1)
except RuntimeError:
    from src.rag import index_documents
    index_documents(chunk_size=512)


if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run_stdio_async())
