"""
Week 4 — Tool definitions + function calling

Tools are real functions the model can decide to call.
The model decides. Your code executes. This boundary is sacred.

Design (single source of truth):
  • Raw functions  — build_status / recent_deploys / active_incidents —
    own the data. Demos wrap these (e.g. to inject failures) without
    re-defining or duplicating anything.
  • @tool wrappers  — get_build_status / get_recent_deploys /
    get_active_incidents — own the schema the model sees. Their
    description is what teaches the model to route.

Imports: from src.llm import get_llm
"""
import json
import time
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from src.llm import get_llm


# ═══════════════════════════════════════════════════════════════
# Tool data — mock implementations of live APIs
# ═══════════════════════════════════════════════════════════════

BUILD_STATUSES = {
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

DEPLOYS = {
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

ACTIVE_INCIDENTS = {
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


# ═══════════════════════════════════════════════════════════════
# Raw functions — the data sources (wrap these in demos/tests)
# ═══════════════════════════════════════════════════════════════

def build_status(service_name: str) -> str:
    """Return the current build/health status of a service as JSON."""
    data = BUILD_STATUSES.get(service_name)
    if data is None:
        return json.dumps({
            "status": "unknown",
            "error": f"No data for service '{service_name}'",
        })
    return json.dumps(data)


def recent_deploys(service_name: str, limit: int = 5) -> str:
    """Return the last N deployments of a service as JSON."""
    service_deploys = DEPLOYS.get(service_name, [])
    return json.dumps(service_deploys[:limit], indent=2)


def active_incidents(service_name: str) -> str:
    """Return any active (unresolved) incidents of a service as JSON."""
    service_incidents = ACTIVE_INCIDENTS.get(service_name, [])
    return json.dumps(service_incidents, indent=2)


# ═══════════════════════════════════════════════════════════════
# Tool wrappers — the schemas the model sees (descriptions teach routing)
# ═══════════════════════════════════════════════════════════════

@tool
def get_build_status(service_name: str) -> str:
    """
    Return the current build/health status for a given service.

    Returns a JSON string with status and last deploy timestamp.
    Status is one of: 'healthy', 'degraded', 'down', 'unknown'.
    """
    return build_status(service_name)


@tool
def get_recent_deploys(service_name: str, limit: int = 5) -> str:
    """
    Return the last N deployments for a given service.

    Each deploy has: sha, author, timestamp, status.
    Status is one of: 'success', 'failed', 'rolling_back'.
    """
    return recent_deploys(service_name, limit)


@tool
def get_active_incidents(service_name: str) -> str:
    """
    Return any active (unresolved) incidents for a given service.

    Returns a JSON list of incident objects with id, severity, and summary.
    """
    return active_incidents(service_name)


# ═══════════════════════════════════════════════════════════════
# Tool execution — the application layer
# ═══════════════════════════════════════════════════════════════

ALL_TOOLS = [get_build_status, get_recent_deploys, get_active_incidents]
TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}

# Upper bound on tool-calling rounds. The model may chain tools (status →
# deploys → incidents); if it never settles on a text answer we force one.
# A model that never stops calling tools is a cost event, not a feature.
MAX_TOOL_TURNS = 6


def flaky(fn, fail_first_n: int = 0, error: type[Exception] = ConnectionError):
    """
    Deterministic failure injection for demos/tests.

    Wraps a raw function (e.g. ``build_status``) so the first
    ``fail_first_n`` calls raise ``error`` and later calls succeed. Each
    wrapper owns its own counter, so scenarios are self-contained — no
    shared global state, no reliance on call order across scenarios.

    Args:
        fn: The function to wrap (a raw data function, not a @tool).
        fail_first_n: Number of initial calls that fail (0 = never fails).
        error: Exception type to raise while failing.

    Returns:
        Wrapped function with the same signature as fn.
    """
    calls = {"made": 0}

    def wrapped(*args, **kwargs):
        calls["made"] += 1
        if calls["made"] <= fail_first_n:
            raise error(f"Simulated failure {calls['made']}/{fail_first_n}")
        return fn(*args, **kwargs)

    wrapped.__name__ = f"flaky_{getattr(fn, '__name__', 'fn')}"
    return wrapped


def _as_text(message) -> str:
    """Extract plain text from an AI message (handles str or content blocks)."""
    content = message.content
    if isinstance(content, str):
        return content.strip()
    try:
        return "".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        ).strip()
    except Exception:
        return str(content).strip()


def _usage_of(message) -> dict:
    """Best-effort token usage from a LangChain message's usage_metadata."""
    md = getattr(message, "usage_metadata", None) or {}
    return {
        "input_tokens": md.get("input_tokens") or 0,
        "output_tokens": md.get("output_tokens") or 0,
        "total_tokens": md.get("total_tokens") or 0,
    }


def execute_tool_safely(tool_call: dict, max_retries: int = 2,
                        tools_by_name: dict | None = None,
                        verbose: bool = False) -> str:
    """
    Execute a tool call with error handling in the application layer.

    Retries on failure, returns a structured error if all retries fail.
    The model sees the result and decides what to do next — but your code
    controls the retry logic, not the model.

    Args:
        tool_call: A tool call dict from the model's response.
        max_retries: Number of retry attempts (default 2).
        tools_by_name: Registry to resolve tool names from. Defaults to
            the module-level ``TOOLS_BY_NAME``. Demos pass a registry that
            maps a tool to a flaky wrapper to exercise retries.
        verbose: If True, print each failed attempt as it retries.

    Returns:
        Tool result as a JSON string, or a structured error string.
    """
    registry = tools_by_name if tools_by_name is not None else TOOLS_BY_NAME
    tool_name = tool_call["name"]
    tool_fn = registry.get(tool_name)

    if tool_fn is None:
        return json.dumps({
            "error": f"Unknown tool: '{tool_name}'",
            "available_tools": list(registry.keys()),
        })

    last_error = None
    for attempt in range(1, max_retries + 2):  # 1 initial + N retries
        try:
            return tool_fn.invoke(tool_call["args"])
        except Exception as e:
            last_error = str(e)
            if attempt <= max_retries:
                if verbose:
                    print(f"       ⚠️  attempt {attempt} failed ({e}) — retrying…")
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

    The loop is bounded but multi-round: the model may chain as many tool
    calls as it needs (e.g. status, then deploys, then incidents). Each tool
    result is injected back into the conversation until the model produces a
    plain-text answer. If it never settles, an unbounded final call forces
    text so the caller always gets an answer, never an empty string.

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

    # Request → Decide → Execute → Return, repeated until the model answers.
    for _ in range(MAX_TOOL_TURNS):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            return _as_text(response)

        for tc in response.tool_calls:
            result = execute_tool_safely(tc)
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    # The model kept calling tools — drop the tools and force a text answer.
    return _as_text(llm.invoke(messages))


def run_tool_loop_with_trace(user_query: str, temperature: float = 0.0) -> dict:
    """
    Same as run_tool_loop, but returns a trace of every step — including
    per-step token usage — for debugging, cost visibility, and demonstration.

    Returns:
        dict with keys: answer, tool_calls, tool_results, steps, usage.
        ``usage`` aggregates input/output/total tokens across every LLM call.
    """
    llm = get_llm(temperature=temperature)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    trace = {"query": user_query, "steps": [], "tool_calls": [], "tool_results": [], "usage": {}}
    messages = [
        SystemMessage(content=(
            "You are a helpful engineering assistant. You have access to tools "
            "that can check service health, deployment history, and active incidents. "
            "Use tools when you need live data. Answer directly for general questions."
        )),
        HumanMessage(content=user_query),
    ]

    def _append_answer_step(text: str, message) -> None:
        usage = _usage_of(message)
        trace["steps"].append({"type": "answer", "content": text, "tokens": usage})
        _accrue(usage)

    usage_totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    def _accrue(usage: dict) -> None:
        for key in usage_totals:
            usage_totals[key] += usage.get(key, 0)

    for _ in range(MAX_TOOL_TURNS):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        usage = _usage_of(response)
        _accrue(usage)
        trace["steps"].append({
            "type": "decide",
            "content": str(response.content)[:200],
            "tokens": usage,
        })

        if not response.tool_calls:
            trace["answer"] = _as_text(response)
            _append_answer_step(trace["answer"], response)
            trace["usage"] = usage_totals
            return trace

        for tc in response.tool_calls:
            trace["tool_calls"].append({"name": tc["name"], "args": tc["args"]})
            result = execute_tool_safely(tc)
            trace["tool_results"].append({"tool": tc["name"], "result": result[:200]})
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))
            trace["steps"].append({"type": "execute", "tool": tc["name"], "result": result[:200]})

    # The model kept calling tools — drop the tools and force a text answer.
    final = llm.invoke(messages)
    trace["answer"] = _as_text(final)
    _append_answer_step(trace["answer"], final)
    trace["usage"] = usage_totals
    return trace
