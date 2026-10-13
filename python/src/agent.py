"""
Week 6 — Agent Orchestrator: Multi-Step Workflows

A state-machine agent composed from the modules built in Weeks 1-5:

    from src.llm import get_llm                 # Week 1 — provider
    from src.schemas import (                   # Week 2 — typed contracts
        AgentAnswer, BuildStatus, DeployRecord, Incident,
        ReadinessVerdict, EvidenceChunk,
    )
    from src.rag import retrieve                # Week 3 — retrieval
    call_tool(...)                              # THE SEAM: Week 4 execution
                                                # semantics over the Week 5
                                                # MCP server (or local W4 tools)

State is explicit and typed:
  - every data field is a contract (or None — "not checked yet"),
  - every transition is RECORDED in the audit trail (`messages`),
  - every failure is SURFACED in `error`, never swallowed.

The report is a structured AgentAnswer — Week 2 validators run on the
agent's own output before anyone reads it.
"""
import os, sys, json, time, asyncio
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from src.llm import get_llm
from src.schemas import (
    AgentAnswer,
    BuildStatus,
    DeployRecord,
    EvidenceChunk,
    Incident,
    ReadinessVerdict,
)
from src.rag import retrieve


# ═══════════════════════════════════════════════════════════════
# call_tool — THE SEAM
# ═══════════════════════════════════════════════════════════════
# One way for every node to reach a tool. The backend is a config
# decision, not an architecture fork:
#
#   TOOL_BACKEND=mcp    (default) — Week 5 server over SSE, RAG-backed
#   TOOL_BACKEND=local            — Week 4 src.tools in-process
#
# Same tool names, same contracts, same retry policy — swap the wire,
# not the code. Transport + parsing + contract validation are retried
# as ONE unit; when retries are exhausted the failure is a structured
# ToolFailure, never a crash and never a silent None.

MCP_URL = "http://127.0.0.1:8000/sse"
TOOL_MAX_RETRIES = 2


class ToolFailure(Exception):
    """All retries exhausted. Carries context for the audit trail."""


def _transport_mcp(name: str, args: dict) -> str:
    """Week 5 backend: SSE client to the long-lived server."""
    async def _call():
        from mcp.client.sse import sse_client
        from mcp import ClientSession
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, args)
                return result.content[0].text if result.content else "no result"
    return asyncio.run(_call())


def _transport_local(name: str, args: dict) -> str:
    """Week 4 backend: in-process tools through execute_tool_safely's
    registry + structured-failure contract (retries live at the seam)."""
    from src.tools import execute_tool_safely  # Week 4 — imported, not copied
    raw = execute_tool_safely({"name": name, "args": args}, max_retries=0)
    data = json.loads(raw)
    if isinstance(data, dict) and (
        data.get("status") == "failed" or "available_tools" in data
    ):
        raise ToolFailure(f"{name}: {data.get('error')}")
    return raw


def _looks_like_failure(data) -> bool:
    """Structured failure markers shared by both backends."""
    return isinstance(data, dict) and (
        data.get("status") == "failed" or "available_tools" in data
    )


def call_tool(name: str, args: dict, contract=None, many: bool = False,
              max_retries: int = TOOL_MAX_RETRIES):
    """
    Call a tool and return a VALIDATED contract.

    Args:
        name:    tool name (identical on both backends)
        args:    tool arguments
        contract: Pydantic model to validate the result into (None = raw text)
        many:    result is a list of contracts, not one
        max_retries: attempts for transport AND contract failures alike

    Returns:
        contract instance (or list of them), or raw string if contract is None.

    Raises:
        ToolFailure: after max_retries+1 attempts — structured, never a crash.
    """
    backend = os.environ.get("TOOL_BACKEND", "mcp").strip().lower()
    transport = _transport_local if backend == "local" else _transport_mcp

    last = None
    for attempt in range(1, max_retries + 2):
        try:
            raw = transport(name, args)
            if contract is None:
                return raw
            data = json.loads(raw)
            if _looks_like_failure(data):
                raise ToolFailure(f"{name}: {data.get('error') or data}")
            if many:
                if not isinstance(data, list):
                    raise ToolFailure(
                        f"{name}: expected an array, got {type(data).__name__}")
                return [contract.model_validate(item) for item in data]
            return contract.model_validate(data)
        except Exception as e:  # transport, parse, or contract violation
            last = e
            if attempt <= max_retries:
                time.sleep(1)  # backoff before retry — mirrors Week 4

    raise ToolFailure(
        f"{name}: failed after {max_retries + 1} attempt(s) — "
        f"{type(last).__name__}: {last}"
    )


# ═══════════════════════════════════════════════════════════════
# Agent State — carried across all steps
# ═══════════════════════════════════════════════════════════════

class AgentState(TypedDict):
    query: str
    service_name: str
    context: str
    build_status: Optional[BuildStatus]      # None = not checked yet
    deploys: Optional[list[DeployRecord]]    # None = not checked yet
    incidents: Optional[list[Incident]]      # None = not checked yet
    report: Optional[AgentAnswer]            # None = not generated yet
    steps: int
    cost: float
    error: str                               # "" = no failure so far
    messages: list[dict]                     # audit trail — recorded, never reconstructed


def _record(state: AgentState, step: str, **detail) -> None:
    """Append one event to the audit trail. Every node records itself."""
    state["messages"].append({"step": step, **detail})


def _init_state(query: str) -> AgentState:
    """Create a fresh AgentState for a query."""
    return {
        "query": query,
        "service_name": "",
        "context": "",
        "build_status": None,
        "deploys": None,
        "incidents": None,
        "report": None,
        "steps": 0,
        "cost": 0.0,
        "error": "",
        "messages": [],
    }


class _UsageCapture(BaseCallbackHandler):
    """Capture token usage from an LLM call that returns a Pydantic model.

    ``with_structured_output`` hands back a model instance, not a message,
    so usage_metadata is invisible on the result. Callbacks see the
    intermediate message — this is how the cost-per-step promise in the
    docs stays true for structured calls too.
    """

    def __init__(self):
        self.usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    def on_llm_end(self, response, **kwargs):
        try:
            msg = response.generations[0][0].message
            md = getattr(msg, "usage_metadata", None) or {}
            for key in self.usage:
                if md.get(key):
                    self.usage[key] += md[key]
        except Exception:
            pass


def _estimate_cost(response) -> float:
    """Estimate LLM call cost from usage metadata."""
    usage = getattr(response, "usage_metadata", None) or {}
    inp = usage.get("input_tokens", 0) if hasattr(usage, "get") else 0
    out = usage.get("output_tokens", 0) if hasattr(usage, "get") else 0
    return (inp * 0.15 + out * 0.60) / 1_000_000


def _usage_cost(usage: dict) -> float:
    return (usage.get("input_tokens", 0) * 0.15
            + usage.get("output_tokens", 0) * 0.60) / 1_000_000


# ═══════════════════════════════════════════════════════════════
# Nodes — each is one step in the workflow
# ═══════════════════════════════════════════════════════════════

def extract_service(state: AgentState) -> AgentState:
    """Extract the service name from the user's query."""
    if state.get("service_name"):
        _record(state, "extract_service", service=state["service_name"], cached=True)
        return state  # already extracted

    llm = get_llm(temperature=0)
    response = llm.invoke([
        SystemMessage(content=(
            "Extract the service name from the user's query. "
            "Respond with EXACTLY ONE WORD: the service name. "
            "Known services: auth-service, payment-api, inventory-service. "
            "If no service is mentioned, respond with 'payment-api' as default."
        )),
        HumanMessage(content=state["query"]),
    ])
    state["service_name"] = response.content.strip().lower()
    state["steps"] += 1
    state["cost"] += _estimate_cost(response)
    _record(state, "extract_service", service=state["service_name"])
    return state


def retrieve_context(state: AgentState) -> AgentState:
    """Retrieve relevant documents from the RAG index (Week 3)."""
    try:
        chunks = retrieve(state["query"], k=3)
        state["context"] = "\n\n---\n\n".join(chunks) if chunks else "(no relevant documents found)"
        _record(state, "retrieve_context", chunks=len(chunks))
    except Exception as e:
        # Retrieval failed → context stays empty AND the failure is visible.
        state["context"] = ""
        state["error"] = f"retrieve_context: {e}"
        _record(state, "retrieve_context", status="failed", error=str(e))
    state["steps"] += 1
    return state


def _get_service(state: AgentState) -> str:
    """Get the service name from state. Fails if not set."""
    svc = state.get("service_name", "").strip()
    if not svc:
        raise RuntimeError("service_name not set — extract_service must run first")
    return svc


def _tool_failure(state: AgentState, step: str, exc: Exception) -> None:
    """Record a tool/contract failure: field stays None, error is surfaced."""
    state["error"] = f"{step}: {type(exc).__name__}: {exc}"
    _record(state, step, status="failed", error=str(exc))


def check_build(state: AgentState) -> AgentState:
    """get_build_status through the seam → validated BuildStatus contract."""
    svc = _get_service(state)
    try:
        state["build_status"] = call_tool(
            "get_build_status", {"service_name": svc}, contract=BuildStatus)
        _record(state, "check_build", status=state["build_status"].status)
    except Exception as e:
        _tool_failure(state, "check_build", e)
    state["steps"] += 1
    return state


def check_deploys(state: AgentState) -> AgentState:
    """get_recent_deploys through the seam → validated DeployRecord contracts."""
    svc = _get_service(state)
    try:
        state["deploys"] = call_tool(
            "get_recent_deploys", {"service_name": svc, "limit": 3},
            contract=DeployRecord, many=True)
        _record(state, "check_deploys", count=len(state["deploys"]))
    except Exception as e:
        _tool_failure(state, "check_deploys", e)
    state["steps"] += 1
    return state


def check_incidents(state: AgentState) -> AgentState:
    """get_active_incidents through the seam → validated Incident contracts."""
    svc = _get_service(state)
    try:
        state["incidents"] = call_tool(
            "get_active_incidents", {"service_name": svc},
            contract=Incident, many=True)
        _record(state, "check_incidents", count=len(state["incidents"]))
    except Exception as e:
        _tool_failure(state, "check_incidents", e)
    state["steps"] += 1
    return state


def _data_section(label: str, value) -> str:
    """Render one data field for the report prompt.

    None means NOT CHECKED — and it says so, in caps, so the model can't
    mistake an empty state for empty-but-checked data.
    """
    if value is None:
        return f"{label}: NOT CHECKED (step was skipped or failed)"
    if isinstance(value, BaseModel):
        return f"{label}:\n{json.dumps(value.model_dump(), indent=2, default=str)}"
    if isinstance(value, list):
        return f"{label}:\n{json.dumps([v.model_dump() if hasattr(v, 'model_dump') else v for v in value], indent=2, default=str)}"
    return f"{label}:\n{value}"


def generate_report(state: AgentState) -> AgentState:
    """Produce a STRUCTURED AgentAnswer (Week 2 contract) from collected data."""
    llm = get_llm(temperature=0)
    structured = llm.with_structured_output(AgentAnswer)
    capture = _UsageCapture()

    sections = "\n\n".join([
        f"Query: {state['query']}",
        _data_section("Relevant documentation", state["context"] or None),
        _data_section("Build status", state["build_status"]),
        _data_section("Recent deployments", state["deploys"]),
        _data_section("Active incidents", state["incidents"]),
    ])

    system = (
        "You are a site reliability engineer. Answer the user's query using ONLY "
        "the data provided below. Rules:\n"
        "- If a section says NOT CHECKED, say so plainly — never invent data for it.\n"
        "- Set a verdict (ready/blockers/next steps) for readiness or health queries; "
        "leave verdict null for docs or general questions.\n"
        "- verdict.confidence must be 'low' unless evidence supports it.\n"
        "- Every claim must cite its source in evidence: 'rag' for documentation, "
        "'tool' for build/deploy/incident data, 'user' for the query itself.\n"
        "- ready=True with blockers, or ready=False with no blockers, will be "
        "REJECTED by the contract validator — be consistent."
    )

    last_exc = None
    answer = None
    for attempt in (1, 2):  # contract violations are retryable
        try:
            answer = structured.invoke(
                [SystemMessage(content=system), HumanMessage(content=sections)],
                config={"callbacks": [capture]},
            )
            break
        except Exception as e:
            last_exc = e

    if answer is not None:
        state["report"] = answer
        _record(state, "generate_report",
                ready=answer.verdict.ready if answer.verdict else None,
                evidence=len(answer.evidence))
    else:
        # Contract violation at the boundary: surfaced, never hidden.
        state["error"] = f"generate_report: {type(last_exc).__name__}: {last_exc}"
        state["report"] = AgentAnswer(
            answer="(report generation failed — the model's output did not satisfy "
                   "the AgentAnswer contract. See error.)",
        )
        _record(state, "generate_report", status="failed", error=str(last_exc))
    state["steps"] += 1
    state["cost"] += _usage_cost(capture.usage)
    return state


def format_report(report: Optional[AgentAnswer]) -> str:
    """Render an AgentAnswer for humans. Shared by every demo."""
    if report is None:
        return "(no report generated)"
    lines = [report.answer]
    if report.verdict is not None:
        v = report.verdict
        lines.append("")
        lines.append(f"  ready      : {v.ready}  (confidence: {v.confidence})")
        for b in v.blockers:
            lines.append(f"  blocker    : {b}")
        for n in v.recommended_next_steps:
            lines.append(f"  next step  : {n}")
    if report.evidence:
        lines.append("")
        for e in report.evidence:
            score = f" ({e.relevance_score})" if e.relevance_score is not None else ""
            lines.append(f"  evidence[{e.source}]{score}: {e.content[:100]}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Router — model decides the next step dynamically
# ═══════════════════════════════════════════════════════════════

def router(state: AgentState) -> str:
    """Model decides which step to run next based on the query and current state."""
    llm = get_llm(temperature=0)
    response = llm.invoke([
        SystemMessage(content=(
            "You are a workflow router. Based on the user's query and what data "
            "has already been collected, decide the NEXT step to run. "
            "Respond with EXACTLY ONE WORD from this list:\n\n"
            "- retrieve   (if the query asks about documentation or context)\n"
            "- check_build   (ONLY if the query asks about health, status, healthy, or readiness)\n"
            "- check_deploys (ONLY if the query asks about deployments, releases, deployed, or what was deployed)\n"
            "- check_incidents (ONLY if the query asks about incidents, outages, issues, or alerts)\n"
            "- report    (if all NEEDED data has been collected for this specific query)\n"
            "- done      (if the task is complete or cannot proceed)\n\n"
            "IMPORTANT: Only run steps the query explicitly asks for. "
            "If the query asks about docs/APIs/endpoints/SLA/specs → ONLY retrieve. Skip all tools. "
            "If the query only asks about health/status → ONLY check_build. Skip deploys and incidents. "
            "If the query only asks about deployments → ONLY check_deploys. Skip build and incidents. "
            "If the query only asks about incidents → ONLY check_incidents. Skip build and deploys. "
            "Only run ALL steps if the query asks for 'full assessment' or 'full report' or 'everything'. "
            "Do NOT cascade. 'healthy?' does NOT mean 'also check incidents'."
        )),
        HumanMessage(content=(
            f"QUERY: {state['query']}\n\n"
            f"CURRENT STATE:\n"
            f"- Steps completed: {state['steps']}\n"
            f"- Context retrieved: {'YES' if state['context'] else 'NO'}\n"
            f"- Build status checked: {'YES' if state['build_status'] else 'NO'}\n"
            f"- Deploys checked: {'YES' if state['deploys'] else 'NO'}\n"
            f"- Incidents checked: {'YES' if state['incidents'] else 'NO'}\n\n"
            f"NEVER return a step that already has data (YES above). "
            f"If all needed data is YES, return 'report'.\n\n"
            f"Next step:"
        )),
    ])

    decision = response.content.strip().lower()
    state["cost"] += _estimate_cost(response)
    return decision


# ═══════════════════════════════════════════════════════════════
# Guard — stop if limits exceeded
# ═══════════════════════════════════════════════════════════════

MAX_STEPS = 10
MAX_COST = 2.00  # dollars


def guard(state: AgentState) -> str:
    """Stop if limits exceeded. Otherwise, let the router decide."""
    if state["steps"] >= MAX_STEPS:
        return "done"
    if state["cost"] >= MAX_COST:
        return "done"
    return router(state)


# ═══════════════════════════════════════════════════════════════
# Graph builders — fixed chain and dynamic routing
# ═══════════════════════════════════════════════════════════════

def build_fixed_chain() -> StateGraph:
    """
    Fixed 4-step chain: extract → retrieve → build → report.
    Predictable and auditable, but brittle — always the same path.
    """
    graph = StateGraph(AgentState)
    graph.add_node("extract_service", extract_service)
    graph.add_node("retrieve", retrieve_context)
    graph.add_node("check_build", check_build)
    graph.add_node("report", generate_report)
    graph.set_entry_point("extract_service")
    graph.add_edge("extract_service", "retrieve")
    graph.add_edge("retrieve", "check_build")
    graph.add_edge("check_build", "report")
    graph.add_edge("report", END)
    return graph.compile()


def build_dynamic_agent() -> StateGraph:
    """
    Dynamic agent: model decides the next step at runtime.
    Extracts service name from query, then routes dynamically.
    All 4 data-collection nodes available, plus report generation.
    Guard prevents runaway loops.
    """
    graph = StateGraph(AgentState)
    graph.add_node("extract_service", extract_service)
    graph.add_node("retrieve", retrieve_context)
    graph.add_node("check_build", check_build)
    graph.add_node("check_deploys", check_deploys)
    graph.add_node("check_incidents", check_incidents)
    graph.add_node("report", generate_report)

    graph.set_entry_point("extract_service")
    graph.add_edge("extract_service", "retrieve")

    # After each node, the guard routes to the next step (or stops)
    route_map = {
        "retrieve": "retrieve",
        "check_build": "check_build",
        "check_deploys": "check_deploys",
        "check_incidents": "check_incidents",
        "report": "report",
        "done": END,
    }
    for node in ("retrieve", "check_build", "check_deploys", "check_incidents"):
        graph.add_conditional_edges(node, guard, route_map)

    return graph.compile()


# ═══════════════════════════════════════════════════════════════
# Convenience functions
# ═══════════════════════════════════════════════════════════════

def run_fixed_chain(query: str) -> dict:
    """Run the fixed chain. Requires the MCP server + Qdrant."""
    agent = build_fixed_chain()
    return agent.invoke(_init_state(query))


def run_dynamic_agent(query: str) -> dict:
    """Run the dynamic agent. Requires the MCP server + Qdrant."""
    agent = build_dynamic_agent()
    return agent.invoke(_init_state(query))