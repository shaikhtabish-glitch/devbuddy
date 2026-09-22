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
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env for API keys (OPENROUTER_API_KEY needed by get_llm)
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

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

    Wrapped in a try/except so tool calls never crash the MCP protocol. Any error
    is returned as structured JSON the client can always parse.
    """
    try:
        chunks = retrieve(query, k=k)
        context = "\n\n---\n\n".join(chunks) if chunks else "(no data found)"

        llm = get_llm(temperature=0)
        response = llm.invoke([
            SystemMessage(content=(
                "You are a data extraction tool. "
                "Only use data present in the provided context. Do not invent information. "
                "Return ONLY valid JSON (object or array) — no markdown, no prose.\n\n"
                "If no relevant data is found in the context, return a JSON object "
                "with 'status': 'unknown' and 'reason': 'no matching data found'.\n\n"
                f"{instructions}"
            )),
            HumanMessage(content=f"Context:\n{context}")
        ])
        text = response.content.strip()
        # Strip markdown fences
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3].strip()
        # Validate — fallback to structured unknown if not valid JSON
        try:
            json.loads(text)
            return text
        except (json.JSONDecodeError, ValueError):
            return json.dumps({"status": "unknown", "reason": "could not parse tool result"})
    except Exception as e:
        return json.dumps({
            "status": "unknown",
            "reason": f"tool error: {type(e).__name__} — {str(e)}"
        })

# ── Tools ─────────────────────────────────────────────────────
_rate_limits = {"get_build_status": {"count": 0, "window_start": time.time()}}

def _check_rate_limit(tool_name: str, limit: int = 3, window_seconds: int = 10):
    """Real rate limiting implementation."""
    now = time.time()
    state = _rate_limits.setdefault(tool_name, {"count": 0, "window_start": now})
    
    if now - state["window_start"] > window_seconds:
        state["count"] = 1
        state["window_start"] = now
    else:
        state["count"] += 1
        if state["count"] > limit:
            raise ValueError(f"RateLimitExceeded: Tool '{tool_name}' called too many times. Limit {limit} per {window_seconds}s.")

@mcp.tool()
def get_build_status(service_name: str) -> str:
    """Return the current build/health status for a given service."""
    _check_rate_limit("get_build_status", limit=3, window_seconds=30)
    return _synthesise(
        instructions=(
            "Extract the current build/health status for the given service. "
            "Return JSON with 'status' (one of: healthy, degraded, down, unknown) "
            "and 'last_deploy' (ISO timestamp). "
        ),
        query=f"{service_name} build status health check deploy",
    )


@mcp.tool()
def delete_incident_record(incident_id: str, admin_token: str) -> str:
    """
    DESTRUCTIVE TOOL: Delete an incident record.
    Requires an out-of-band admin_token to simulate Human-In-The-Loop approval.
    """
    if admin_token != "super-secret-approval-123":
        return json.dumps({"status": "error", "reason": "Unauthorized. Invalid admin_token."})
    return json.dumps({"status": "success", "deleted": incident_id})

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


# ── Resources ───────────────────────────────────────────────────

@mcp.resource("file://shared/data/{filename}")
def get_shared_document(filename: str) -> str:
    """Read a document from the shared/data directory."""
    # Ensure it only reads from shared/data
    safe_name = os.path.basename(filename)
    filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "shared", "data", safe_name)
    try:
        with open(filepath, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading resource: {e}"


# ── Prompts ─────────────────────────────────────────────────────

@mcp.prompt()
def incident_analysis_prompt(service_name: str) -> str:
    """A standard prompt for analyzing service incidents."""
    return (
        f"You are a Site Reliability Engineer. Analyze the recent incidents "
        f"and deployments for {service_name}. Use the 'get_active_incidents' "
        f"and 'get_recent_deploys' tools to gather data. "
        f"Also read the SLA resource for the service if available. "
        f"Provide a root cause hypothesis and an action plan."
    )


# ── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    # SSE transport — long-lived daemon. Model loads once, all clients share it.
    mcp.run(transport="sse")
