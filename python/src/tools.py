"""
Week 4 — Tool definitions + function calling

Tools are real functions the model can decide to call.
The model decides. Your code executes. This boundary is sacred.

Imports: from src.llm import get_llm
"""
import json
import random
import time
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from src.llm import get_llm


# ═══════════════════════════════════════════════════════════════
# Tool definitions — mock implementations of live APIs
# ═══════════════════════════════════════════════════════════════

@tool
def get_build_status(service_name: str) -> str:
    """
    Return the current build/health status for a given service.

    Returns a JSON string with status and last deploy timestamp.
    Status is one of: 'healthy', 'degraded', 'down', 'unknown'.
    """
    statuses = {
        "auth-service": {
            "status": "healthy",
            "last_deploy": "2026-06-28T08:15:00Z",
        },
        "payment-api": {
            "status": "degraded",
            "last_deploy": "2026-06-28T06:45:00Z",
            "failing_since": "2026-06-28T07:30:00Z",
        },
        "inventory-service": {
            "status": "unknown",
            "last_deploy": "2026-06-20T11:00:00Z",
        },
    }
    data = statuses.get(service_name)
    if data is None:
        return json.dumps({
            "status": "unknown",
            "error": f"No data for service '{service_name}'",
        })
    return json.dumps(data)


@tool
def get_recent_deploys(service_name: str, limit: int = 5) -> str:
    """
    Return the last N deployments for a given service.

    Each deploy has: sha, author, timestamp, status.
    Status is one of: 'success', 'failed', 'rolling_back'.
    """
    deploys = {
        "auth-service": [
            {"sha": "abc123def456", "author": "tabish", "timestamp": "2026-06-28T08:15:00Z", "status": "success"},
            {"sha": "789ghi012jkl", "author": "alex", "timestamp": "2026-06-27T14:30:00Z", "status": "success"},
        ],
        "payment-api": [
            {"sha": "def789ghi012", "author": "maria", "timestamp": "2026-06-28T06:45:00Z", "status": "success"},
            {"sha": "jkl345mno678", "author": "maria", "timestamp": "2026-06-27T22:00:00Z", "status": "rolling_back"},
            {"sha": "pqr901stu234", "author": "jordan", "timestamp": "2026-06-27T20:15:00Z", "status": "failed"},
        ],
        "inventory-service": [],
    }
    service_deploys = deploys.get(service_name, [])
    return json.dumps(service_deploys[:limit], indent=2)


@tool
def get_active_incidents(service_name: str) -> str:
    """
    Return any active (unresolved) incidents for a given service.

    Returns a JSON list of incident objects with id, severity, and summary.
    """
    incidents = {
        "payment-api": [
            {
                "id": "INC-842",
                "severity": "Sev1",
                "summary": "payment-api latency spike. 15% of requests affected. Error code 408.",
                "status": "investigating",
            },
        ],
        "auth-service": [],
        "inventory-service": [
            {
                "id": "INC-901",
                "severity": "Sev3",
                "summary": "inventory-service data inconsistency between primary and replica.",
                "status": "investigating",
                "tracking": ["PROJ-891", "PROJ-892"],
            },
        ],
    }
    service_incidents = incidents.get(service_name, [])
    return json.dumps(service_incidents, indent=2)


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
    for attempt in range(1, max_retries + 2):  # 1 initial + N retries
        try:
            return tool_fn.invoke(tool_call["args"])
        except Exception as e:
            last_error = str(e)
            if attempt <= max_retries:
                time.sleep(1)  # backoff before retry
            continue

    # All retries exhausted — return structured error
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

    1. Send the user query to the LLM with tools bound.
    2. If the model returns a tool call, execute it (with error handling).
    3. Inject the result back into the conversation.
    4. Ask the model to produce a final answer.

    Args:
        user_query: The user's question.
        temperature: 0.0 for deterministic output.

    Returns:
        The model's final answer after any tool calls.
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

    # Step 1 + 2: Request → Decide
    response = llm_with_tools.invoke(messages)
    messages.append(response)

    # Step 3 + 4: Execute (if tools were called) → Return
    if response.tool_calls:
        for tc in response.tool_calls:
            result = execute_tool_safely(tc)
            messages.append(ToolMessage(
                content=result,
                tool_call_id=tc["id"],
            ))

        # Step 5: Answer (with tool results in context)
        final = llm_with_tools.invoke(messages)
        return final.content.strip()

    # No tool calls — model answered directly
    return response.content.strip()


def run_tool_loop_with_trace(user_query: str, temperature: float = 0.0) -> dict:
    """
    Same as run_tool_loop, but returns a trace of every step
    for debugging and demonstration.

    Returns:
        dict with keys: answer, tool_calls, tool_results, steps
    """
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
            messages.append(ToolMessage(
                content=result,
                tool_call_id=tc["id"],
            ))
            trace["steps"].append({"type": "execute", "tool": tc["name"], "result": result[:200]})

        final = llm_with_tools.invoke(messages)
        trace["answer"] = final.content.strip()
        trace["steps"].append({"type": "answer", "content": final.content.strip()})
    else:
        trace["answer"] = response.content.strip()
        trace["steps"].append({"type": "answer", "content": response.content.strip()})

    return trace
