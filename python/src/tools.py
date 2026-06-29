"""
Week 4 — Tool definitions + function calling

Tools retrieve data from Qdrant and synthesize it with an LLM.
No hardcoded mock data — real retrieval from indexed documents.

The model decides. Your code executes. This boundary is sacred.

Imports: from src.llm import get_llm
"""
import json
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from src.llm import get_llm
from src.rag import retrieve, hybrid_search


def _synthesize(query_type: str, service_name: str, chunks: list[str]) -> str:
    """
    Feed retrieved chunks to the LLM and synthesize a concise JSON result.
    Only returns data relevant to the query type — not everything in the chunks.
    """
    context = "\n\n---\n\n".join(chunks) if chunks else "(no data found)"
    llm = get_llm(temperature=0)

    type_prompts = {
        "build/health status": (
            "Extract ONLY the current build/health status. Return JSON with 'status' "
            "(one of: healthy, degraded, down, unknown) and 'last_deploy' (ISO timestamp). "
            "Look for the MOST RECENT deployment by date/timestamp. "
            "If the most recent deploy was 'success', status = healthy. "
            "If the most recent deploy was 'rolling_back' or 'failed', status = degraded. "
            "If there are multiple deploys, use the LATEST one. Ignore older deploys. "
            "If health check returns ok AND deploys are fine, status = healthy. "
            "If no build/health data found, status = unknown. "
            "DO NOT include SLA, incidents, endpoints, or other unrelated data."
        ),
        "deployment history": (
            "Extract ONLY deployment history. Return a JSON array of deploys, each with: "
            "service, version, date, sha, author, status (success/failed/rolling_back). "
            "DO NOT include incidents, SLA, health checks, or other unrelated data."
        ),
        "active incidents": (
            "Extract ONLY active (unresolved) incidents. Return a JSON array of incidents, "
            "each with: id, severity, date, summary, status (investigating/resolved). "
            "Skip incidents with status 'Resolved'. "
            "DO NOT include deployments, SLA, health checks, or other unrelated data."
        ),
    }

    instructions = type_prompts.get(query_type, "Extract the requested information.")

    response = llm.invoke([
        SystemMessage(content=(
            "You are a data extraction tool. "
            f"{instructions}\n\n"
            "RULES:\n"
            "- Only use data present in the provided chunks. Do not invent.\n"
            "- If no relevant data is found, return {\"status\": \"unknown\"}\n"
            "- Return ONLY valid JSON, no markdown, no explanation.\n"
            "- Be CONCISE. Return only what was asked for, nothing extra."
        )),
        HumanMessage(content=f"Service: {service_name}\n\nRetrieved chunks:\n{context}"),
    ])

    return response.content.strip()


# ═══════════════════════════════════════════════════════════════
# Tool definitions — Qdrant-backed, LLM-synthesized
# ═══════════════════════════════════════════════════════════════

@tool
def get_build_status(service_name: str) -> str:
    """
    Return the current build/health status for a given service.
    Retrieves data from Qdrant and synthesizes with an LLM.
    Status is one of: healthy, degraded, down, unknown.
    """
    query = f"{service_name} deployment success failed rolling_back"
    chunks = retrieve(query, k=4)
    return _synthesize("build/health status", service_name, chunks)


@tool
def get_recent_deploys(service_name: str, limit: int = 5) -> str:
    """
    Return the last N deployments for a given service.
    Retrieves deployment history from Qdrant and synthesizes with an LLM.
    Each deploy has: sha, author, timestamp, status.
    """
    query = f"{service_name} deploy SHA author timestamp status"
    chunks = hybrid_search(query, k=4)
    raw = _synthesize("deployment history", service_name, chunks)
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            data = data[:limit]
        return json.dumps(data, indent=2)
    except json.JSONDecodeError:
        return raw


@tool
def get_active_incidents(service_name: str) -> str:
    """
    Return any active (unresolved) incidents for a given service.
    Retrieves incident data from Qdrant and synthesizes with an LLM.
    Returns a JSON list of incident objects with id, severity, and summary.
    """
    query = f"{service_name} INC- Sev severity investigating unresolved"
    chunks = hybrid_search(query, k=4)
    return _synthesize("active incidents", service_name, chunks)


# ═══════════════════════════════════════════════════════════════
# Tool execution — the application layer
# ═══════════════════════════════════════════════════════════════

ALL_TOOLS = [get_build_status, get_recent_deploys, get_active_incidents]
TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}


def execute_tool_safely(tool_call: dict, max_retries: int = 2) -> str:
    """
    Execute a tool call with error handling in the application layer.

    Retries on failure, returns a structured error if all retries fail.
    The model sees the result and decides what to do next — but your code
    controls the retry logic, not the model.

    Args:
        tool_call: A tool call dict from the model's response.
        max_retries: Number of retry attempts (default 2).

    Returns:
        Tool result as a JSON string, or a structured error string.
    """
    tool_name = tool_call["name"]
    tool_fn = TOOLS_BY_NAME.get(tool_name)

    if tool_fn is None:
        return json.dumps({
            "error": f"Unknown tool: '{tool_name}'",
            "available_tools": list(TOOLS_BY_NAME.keys()),
        })

    last_error = None
    for attempt in range(1, max_retries + 2):
        try:
            return tool_fn.invoke(tool_call["args"])
        except Exception as e:
            last_error = str(e)
            if attempt <= max_retries:
                import time
                time.sleep(1)
                continue

    return json.dumps({
        "error": last_error,
        "tool": tool_name,
        "status": "failed",
        "attempts": max_retries + 1,
        "hint": "The tool is temporarily unavailable. Try a different approach.",
    })


def run_tool_loop(user_query: str, temperature: float = 0.0) -> str:
    """
    Full tool-calling loop: Request → Decide → Execute → Return → Answer.
    """
    llm = get_llm(temperature=temperature)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    messages = [
        SystemMessage(content=(
            "You are a helpful engineering assistant. You have access to tools "
            "that can check service health, deployment history, and active incidents. "
            "Use tools when you need live data. Answer directly for general questions."
        )),
        HumanMessage(content=user_query),
    ]

    response = llm_with_tools.invoke(messages)
    messages.append(response)

    if response.tool_calls:
        for tc in response.tool_calls:
            result = execute_tool_safely(tc)
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

        final = llm_with_tools.invoke(messages)
        return final.content.strip()

    return response.content.strip()


def run_tool_loop_with_trace(user_query: str, temperature: float = 0.0) -> dict:
    """Same as run_tool_loop, but returns a trace of every step."""
    llm = get_llm(temperature=temperature)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    trace = {"query": user_query, "steps": []}
    messages = [
        SystemMessage(content=(
            "You are a helpful engineering assistant. You have access to tools "
            "that can check service health, deployment history, and active incidents. "
            "Use tools when you need live data. Answer directly for general questions."
        )),
        HumanMessage(content=user_query),
    ]

    response = llm_with_tools.invoke(messages)
    messages.append(response)
    trace["steps"].append({"type": "decide", "content": str(response.content)[:200]})

    if response.tool_calls:
        trace["tool_calls"] = [
            {"name": tc["name"], "args": tc["args"]}
            for tc in response.tool_calls
        ]
        trace["tool_results"] = []

        for tc in response.tool_calls:
            result = execute_tool_safely(tc)
            trace["tool_results"].append({
                "tool": tc["name"],
                "result": result[:200],
            })
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))
            trace["steps"].append({"type": "execute", "tool": tc["name"], "result": result[:200]})

        final = llm_with_tools.invoke(messages)
        trace["answer"] = final.content.strip()
        trace["steps"].append({"type": "answer", "content": final.content.strip()})
    else:
        trace["answer"] = response.content.strip()
        trace["steps"].append({"type": "answer", "content": response.content.strip()})

    return trace
