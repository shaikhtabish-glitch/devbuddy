"""
Week 5 — MCP Server: Shared Tool Ecosystem

Exposes tools over the Model Context Protocol. Each tool retrieves data
from the Week 3 RAG index (Qdrant) and synthesises it with the LLM —
no hardcoded mock data. The same vector store that grounded answers in
Week 3 now powers tool results in Week 5. One data source, many consumers.

Write once. Any MCP client in any language can discover and call these tools.

Imports: from src.rag import retrieve, index_documents
         from src.llm import get_llm
         from langchain_core.messages import HumanMessage, SystemMessage
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from langchain_core.messages import HumanMessage, SystemMessage
from src.rag import retrieve, index_documents
from src.llm import get_llm

mcp = FastMCP(
    name="devbuddy-mcp",
    instructions=(
        "DevBuddy MCP Server — exposes build status, deployment history, "
        "and active incident data for engineering services. "
        "All data comes from the Week 3 RAG index (Qdrant)."
    ),
)


# ── Startup: ensure the RAG index exists before serving tools ──

try:
    count = index_documents()
    print(f"RAG index ready: {count} chunks indexed", file=sys.stderr)
except Exception as e:
    print(f"WARNING: Could not index documents — {e}", file=sys.stderr)
    print("Make sure Qdrant is running: docker-compose up -d", file=sys.stderr)


# ── Helper: retrieve + synthesise ─────────────────────────────

def _synthesise(instructions: str, query: str, k: int = 5) -> str:
    """Retrieve relevant chunks from the RAG index and synthesise JSON with the LLM.

    Assumes documents have already been indexed (Week 3). If the index doesn't
    exist, retrieve() raises a clear RuntimeError — index first, then use tools.
    """
    chunks = retrieve(query, k=k)
    context = "\n\n---\n\n".join(chunks) if chunks else "(no data found)"

    llm = get_llm(temperature=0)
    response = llm.invoke([
        SystemMessage(content=(
            "You are a data extraction tool. "
            "Only use data present in the provided context. Do not invent information. "
            "Return ONLY raw JSON — no markdown fences, no backticks, no explanations. "
            f"{instructions}"
        )),
        HumanMessage(content=f"Context:\n{context}")
    ])
    # Strip markdown fences if the model added them anyway
    text = response.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


# ── Tools ─────────────────────────────────────────────────────

@mcp.tool()
def get_build_status(service_name: str) -> str:
    """
    Return the current build/health status for a given service.
    Searches the RAG index for build status, health checks, and deployment data.
    Returns a JSON string with status (healthy/degraded/down/unknown)
    and last_deploy timestamp.
    """
    return _synthesise(
        instructions=(
            "Extract the current build/health status for the given service. "
            "Return JSON with 'status' (one of: healthy, degraded, down, unknown) "
            "and 'last_deploy' (ISO timestamp). "
            "Look for the MOST RECENT deployment by date. "
            "If the most recent deploy was 'success', status = healthy. "
            "If the most recent deploy was 'rolling_back' or 'failed', status = degraded. "
            "If no build/health data is found, status = unknown."
        ),
        query=f"{service_name} build status health check deploy",
    )


@mcp.tool()
def get_recent_deploys(service_name: str, limit: int = 5) -> str:
    """
    Return the last N deployments for a given service.
    Searches the RAG index for deployment history.
    Returns a JSON array of deploy objects, each with:
    sha, author, timestamp, status (success/failed/rolling_back).
    """
    return _synthesise(
        instructions=(
            "Extract ONLY deployment history for the given service. "
            "Return a JSON array of deploys, each with: "
            "sha, author, timestamp, status (success/failed/rolling_back). "
            "Sort by timestamp descending (most recent first). "
            f"Return at most {limit} entries. "
            "If no deployment data is found, return an empty array []."
        ),
        query=f"{service_name} deployment history deploy",
    )


@mcp.tool()
def get_active_incidents(service_name: str) -> str:
    """
    Return any active (unresolved) incidents for a given service.
    Searches the RAG index for incident reports.
    Returns a JSON array of incident objects with:
    id, severity, date, summary, status (investigating/resolved).
    Only returns unresolved incidents.
    """
    return _synthesise(
        instructions=(
            "Extract ONLY active (unresolved) incidents for the given service. "
            "Return a JSON array of incidents, each with: "
            "id, severity, date, summary, status (investigating/resolved). "
            "Skip incidents with status 'resolved' — only include active ones. "
            "If no incidents are found, return an empty array []."
        ),
        query=f"{service_name} incident outage alert",
    )


@mcp.tool()
def search_docs(query: str, k: int = 3) -> str:
    """Search the documentation index for relevant context.
    Returns the top-k most relevant document chunks as a JSON array of strings.
    Use this to find documentation, setup guides, API specs, or any written knowledge."""
    chunks = retrieve(query, k=k)
    return json.dumps(chunks, indent=2)


# ── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
