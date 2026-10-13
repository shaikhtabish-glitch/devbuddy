"""
Week 6 — Agent Orchestrator: Multi-Step Workflows

A state-machine agent composed from the modules built in Weeks 1-5:

    from src.llm import get_llm                 # Week 1 — provider
    from src.schemas import (                   # Week 2 — typed contracts
        AgentAnswer, BuildStatus, DeployRecord, Incident,
        ReadinessVerdict, EvidenceChunk,
    )
    from src.rag import retrieve                # Week 3 — local retrieval backend
    call_tool(...)    # THE SEAM — tools     (W4 execution semantics over the
    read_resource(...) #                      W5 server, or in-process W4 tools)
    get_prompt(...)   #                      — W5 prompts, with local fallback

State is explicit and typed:
  - every data field is a contract (or None — "not checked yet"),
  - every transition is RECORDED in the audit trail (`messages`),
  - every failure is SURFACED in `error`, never swallowed.

The report is a structured AgentAnswer — Week 2 validators run on the
agent's own output before anyone reads it.
"""
import os, sys, json, time, re, asyncio
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

SHARED_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "shared", "data")

# Service → shared document (a W5 Resource the agent grounds with).
SERVICE_RESOURCES = {
    "auth-service": "auth-service-spec.md",
    "payment-api": "payment-api-spec.md",
    "inventory-service": "inventory-service-sla.md",
}


def _backend() -> str:
    """mcp (default) | local — one config flip, same code."""
    return os.environ.get("TOOL_BACKEND", "mcp").strip().lower()


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
    registry + structured-failure contract (retries live at the seam).
    search_docs maps to Week 3 retrieval directly — same contract,
    different wiring, zero protocol overhead."""
    if name == "search_docs":
        chunks = retrieve(args.get("query", ""), k=int(args.get("k", 3)))
        return json.dumps(chunks)
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
    backend = _backend()
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


def read_resource(filename: str) -> str:
    """THE SEAM for W5 Resources: filesystem (local) or protocol (mcp)."""
    safe = os.path.basename(filename)
    if _backend() == "local":
        try:
            with open(os.path.join(SHARED_DATA_DIR, safe)) as f:
                return f.read()
        except OSError as e:
            raise ToolFailure(f"resource {safe}: {e}")

    uri = f"file://shared/data/{safe}"

    async def _call():
        from mcp.client.sse import sse_client
        from mcp import ClientSession
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.read_resource(uri)
                content = result.contents[0]
                return content.text if hasattr(content, "text") else str(content)

    try:
        return asyncio.run(_call())
    except Exception as e:
        raise ToolFailure(f"resource {safe}: {e}")


def get_prompt(name: str, arguments: dict) -> str | None:
    """THE SEAM for W5 Prompts. Returns the server's prompt text, or None
    when the backend has no prompt catalogue (local) — callers fall back
    to their own system prompt. Prompts are workflows-as-protocol."""
    if _backend() == "local":
        return None

    async def _call():
        from mcp.client.sse import sse_client
        from mcp import ClientSession
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.get_prompt(name, arguments)
                content = result.messages[0].content
                if hasattr(content, "text"):
                    return content.text
                if isinstance(content, dict):
                    return content.get("text", "")
                return str(content)

    try:
        return asyncio.run(_call())
    except Exception as e:
        raise ToolFailure(f"prompt {name}: {e}")


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
    next_step: str                           # planner's accepted decision
    steps: int
    cost: float
    error: str                               # "" = no failure so far
    messages: list[dict]                     # audit trail — recorded, never reconstructed


def _record(state: AgentState, step: str, **detail) -> None:
    """Append one event to the audit trail. Every node records itself,
    and carries the COST DELTA since the previous event — so per-step
    cost is traceable, not just the run total."""
    prev_total = sum(m.get("cost", 0.0) for m in state["messages"])
    state["messages"].append(
        {"step": step, **detail, "cost": round(state["cost"] - prev_total, 6)})


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
        "next_step": "",
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
    name = response.content.strip().lower()
    if not name:
        # empty completion (provider quirk at temp=0) — retry once
        response = llm.invoke([
            HumanMessage(content=f"{state['query']}\n\nService name:"),
        ])
        name = response.content.strip().lower() or "payment-api"
    state["service_name"] = name
    state["steps"] += 1
    state["cost"] += _estimate_cost(response)
    _record(state, "extract_service", service=state["service_name"])
    return state


def retrieve_context(state: AgentState) -> AgentState:
    """Ground the query through the seam:

    1. search_docs — retrieval as a tool (mcp: server's W3 index over the
       protocol; local: rag.retrieve in-process — same contract either way),
    2. the service's shared Resource (W5 primitive) — specs/SLA enrich the
       context. Resource failure is recorded but never fatal: docs are
       enrichment, tools are the data path.
    """
    try:
        raw = call_tool("search_docs", {"query": state["query"], "k": 3})
        chunks = json.loads(raw)
        if not isinstance(chunks, list):
            raise ToolFailure(f"search_docs: expected an array, got {raw[:120]}")
        state["context"] = ("\n\n---\n\n".join(chunks)
                            if chunks else "(no relevant documents found)")
        _record(state, "retrieve_context", chunks=len(chunks))
    except Exception as e:
        state["context"] = ""
        _tool_failure(state, "retrieve_context", e)
    else:
        filename = SERVICE_RESOURCES.get(state.get("service_name", "").strip())
        if filename:
            try:
                doc = read_resource(filename)
                state["context"] = (
                    f"SERVICE DOCUMENT ({filename}):\n{doc}\n\n{state['context']}")
                _record(state, "retrieve_context", resource=filename)
            except Exception as e:
                _record(state, "retrieve_context", resource=filename,
                        status="failed", error=str(e))
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

    sections = "\n\n".join(
        [part for part in [
            f"Query: {state['query']}",
            _data_section("Relevant documentation", state["context"] or None),
            _data_section("Build status", state["build_status"]),
            _data_section("Recent deployments", state["deploys"]),
            _data_section("Active incidents", state["incidents"]),
            (f"Tool errors encountered (mention if relevant to the query): "
             f"{state['error']}" if state["error"] else None),
        ] if part]
    )

    system = (
        "You are a site reliability engineer. Answer the user's query using ONLY "
        "the data provided below. Rules:\n"
        "- If a section says NOT CHECKED, say so plainly — never invent data for it.\n"
        "- If build status is 'degraded' or 'down', verdict.ready must be False "
        "and blockers must say why.\n"
        "- Set a verdict (ready/blockers/next steps) for readiness or health queries; "
        "leave verdict null for docs or general questions.\n"
        "- verdict.confidence must be 'low' unless evidence supports it.\n"
        "- Every claim must cite its source in evidence: 'rag' for documentation, "
        "'tool' for build/deploy/incident data, 'user' for the query itself.\n"
        "- ready=True with blockers, or ready=False with no blockers, will be "
        "REJECTED by the contract validator — be consistent."
    )

    # W5 Prompt primitive: incident queries adopt the server's standard
    # workflow (prompt-as-protocol), with our grounding rules appended.
    # Local backend has no prompt catalogue → falls back to the default.
    if "incidents" in classify_query(state["query"]).split("+"):
        try:
            workflow = get_prompt("incident_analysis_prompt",
                                  {"service_name": state["service_name"] or "unknown-service"})
            if workflow:
                system = f"{workflow}\n\nGrounding rules:\n{system}"
                _record(state, "generate_report", prompt="incident_analysis_prompt")
        except Exception as e:
            _record(state, "generate_report", prompt="incident_analysis_prompt",
                    status="failed", error=str(e))

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

    # accrue BEFORE recording, so the cost lands on this event's delta
    state["cost"] += _usage_cost(capture.usage)
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
    return state


# ═══════════════════════════════════════════════════════════════
# C2 teaching node — DELIBERATELY UNDEFENDED (demo-04 only)
# ═══════════════════════════════════════════════════════════════

def _naive_section(label: str, value) -> str:
    """The VULNERABLE rendering: missing state becomes '{}'.

    Compare with _data_section, which says NOT CHECKED. Same data,
    two prompts — the difference is the whole C2 lesson.
    """
    if value is None:
        return f"{label}: {{}}"
    return _data_section(label, value)


def generate_report_naive(state: AgentState) -> AgentState:
    """C2 TEACHING NODE — do not use outside demo-04.

    Renders missing state as '{}' and gives the model NO ground rules
    ('only use provided data'). This is the pattern that makes agents
    hallucinate missing steps: the prompt shows an empty build status
    and asks for a complete report — the most probable next token is
    a helpful invention.
    """
    llm = get_llm(temperature=0)
    structured = llm.with_structured_output(AgentAnswer)
    capture = _UsageCapture()

    sections = "\n\n".join([
        f"Query: {state['query']}",
        _naive_section("Relevant documentation", state["context"] or None),
        _naive_section("Build status", state["build_status"]),
        _naive_section("Recent deployments", state["deploys"]),
        _naive_section("Active incidents", state["incidents"]),
    ])

    system = (
        "You are a site reliability engineer. Generate a complete release "
        "readiness report based on the following data. Be specific and "
        "decisive: state the build health, the deployment state, and whether "
        "the service is ready to ship. Return an AgentAnswer."
    )

    try:
        answer = structured.invoke(
            [SystemMessage(content=system), HumanMessage(content=sections)],
            config={"callbacks": [capture]},
        )
        state["cost"] += _usage_cost(capture.usage)  # before the record
        state["report"] = answer
        _record(state, "generate_report_naive",
                ready=answer.verdict.ready if answer.verdict else None)
    except Exception as e:
        state["cost"] += _usage_cost(capture.usage)
        state["error"] = f"generate_report_naive: {type(e).__name__}: {e}"
        state["report"] = AgentAnswer(answer="(naive report failed)")
        _record(state, "generate_report_naive", status="failed", error=str(e))
    state["steps"] += 1
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
# Registry — the single source of truth for what the agent can do
# ═══════════════════════════════════════════════════════════════
# The router's step catalog, the graph's edge map, the guard's
# requirements, and the refusal message are all DERIVED from this
# dict — they cannot drift apart, because there is only one copy.

NODE_REGISTRY: dict[str, dict] = {
    "retrieve": {
        "fn": retrieve_context,
        "data_field": "context",
        "desc": "Search internal documentation for the query (no service needed)",
    },
    "check_build": {
        "fn": check_build,
        "data_field": "build_status",
        "desc": "Get CI/CD build/health status for the service",
    },
    "check_deploys": {
        "fn": check_deploys,
        "data_field": "deploys",
        "desc": "Get recent deployment history for the service",
    },
    "check_incidents": {
        "fn": check_incidents,
        "data_field": "incidents",
        "desc": "Get active (unresolved) incidents for the service",
    },
}

FIELD_TO_STEP = {spec["data_field"]: name for name, spec in NODE_REGISTRY.items()}

# Query category → state fields that MUST be present before a report is
# generated. The validity guard derives "enough data for THIS query"
# from here — not from prompt prose.
REQUIREMENTS = {
    "full": ["build_status", "deploys", "incidents"],
    "readiness": ["build_status", "deploys"],
    "health": ["build_status"],
    "deploys": ["deploys"],
    "incidents": ["incidents"],
    "docs": ["context"],
    "general": [],
    "action": [],   # imperative — refused before validate ever runs
}

# Imperative operational actions — refused deterministically, before any
# LLM call. An agent with no deploy tool must not depend on a lucky prompt
# to refuse a deploy.
IMPERATIVE_ACTIONS = re.compile(
    r"^\s*(deploy|roll\s?back|rollback|restart|scale|delete|kill|shutdown|wipe)\b"
)


def classify_query(query: str) -> str:
    """Deterministic query categories — code, not prompt.

    Returns ALL matched categories joined with '+' (a query asking about
    deployments AND incidents gets both): the planner's allowed steps and
    the guard's requirements are the UNION of every matched category, so
    a multi-intent query never has a legitimate step rejected as
    out-of-scope. Order of matching = priority for the primary label.
    """
    q = query.lower()
    if IMPERATIVE_ACTIONS.match(q):
        return "action"
    if any(w in q for w in ("full", "everything", "all checks", "end-to-end")):
        return "full"
    cats: list[str] = []
    if any(w in q for w in ("ready", "readiness", "release", "assessment", "ship")):
        cats.append("readiness")
    if any(w in q for w in ("incident", "outage", "alert")):
        cats.append("incidents")
    if any(w in q for w in ("deployed", "deployment", "sha", "version")):
        cats.append("deploys")
    if any(w in q for w in ("healthy", "health", "status", "build")):
        cats.append("health")
    # NOTE: no bare "api" — service names like "payment-api" would match
    # every query and silently force the docs category on all of them.
    if any(w in q for w in ("doc", "spec", "endpoint", "sla", "how",
                            "what is", "why", "describe", "explain")):
        cats.append("docs")
    return "+".join(cats) if cats else "general"


def _router_catalog() -> str:
    """The router's step list — GENERATED from the registry."""
    lines = [f"- {name}: {spec['desc']}" for name, spec in NODE_REGISTRY.items()]
    lines.append("- report: every field NEEDED for this query has been collected")
    lines.append("- done: the task is complete or cannot proceed")
    return "\n".join(lines)


# The graph's route map — GENERATED from the registry too.
# 'done' from the planner = "wrap up" → the GUARD decides (report or
# blocked answer). Only 'stop' (budget exhausted) ends the run.
PLAN_ROUTE_MAP = {
    **{name: name for name in NODE_REGISTRY},
    "report": "validate",
    "done": "validate",
    "validate": "validate",   # plan fallback: hand a stuck run to the guard
    "refuse": "refuse",
    "stop": END,
}


def router(state: AgentState, correction: str | None = None) -> str:
    """Model PROPOSES the next step. The registry (in plan()) decides
    whether the proposal is possible — the model never gets to invent
    capabilities."""
    llm = get_llm(temperature=0)
    system = (
        "You are a workflow router. Based on the user's query and what data "
        "has already been collected, propose the NEXT step. Respond with "
        "EXACTLY ONE WORD from this list:\n\n"
        f"{_router_catalog()}\n\n"
        "Rules:\n"
        "- Only run steps the query explicitly asks for. Do NOT cascade: "
        "'healthy?' does not mean 'also check incidents'.\n"
        "- NEVER propose a step whose data is already YES below.\n"
        "- Docs/API/spec/SLA questions → retrieve only. Health/status → check_build "
        "only. Deployments → check_deploys only. Incidents → check_incidents only.\n"
        "- Propose 'report' as soon as everything the query needs is YES.\n"
        "- If instead the query asks you to PERFORM an operational action "
        "(deploy, rollback, restart, scale, delete), respond with that single "
        "action word — it will be checked against the registry.\n"
    )
    if correction:
        system += f"CORRECTION: {correction}\n"

    response = llm.invoke([
        SystemMessage(content=system),
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
    if not decision:
        # empty completion — retry once before trusting an empty proposal
        response = llm.invoke([
            HumanMessage(content=(
                f"QUERY: {state['query']}\n\nAvailable steps:\n{_router_catalog()}\n\n"
                "Next step (one word):"
            )),
        ])
        decision = response.content.strip().lower()
    state["cost"] += _estimate_cost(response)
    return decision


# ═══════════════════════════════════════════════════════════════
# Guards — three kinds, three jobs
# ═══════════════════════════════════════════════════════════════
# 1. budget_guard (operational) — steps/cost ceiling. Stops runaways.
# 2. plan          (structural)  — LLM proposes, the REGISTRY disposes:
#                                 unknown actions refused, repeats
#                                 corrected — in code, not in prompt.
# 3. validate      (business)    — required state present & acceptable
#                                 BEFORE the report; writes the blocked
#                                 report itself, deterministically.

MAX_STEPS = 10
MAX_COST = 2.00  # dollars


def budget_guard(state: AgentState) -> bool:
    """Operational guard: has the run burned its budget?"""
    return state["steps"] >= MAX_STEPS or state["cost"] >= MAX_COST


def _required_missing(state: AgentState, categories: list[str]) -> list[str]:
    """Fields these query categories need that are not present. Shared by
    plan() (fallback decisions) and validate() (the guard itself) — one
    definition of 'enough data for this query'."""
    needed: list[str] = []
    for category in categories:
        for field in REQUIREMENTS[category]:
            if field not in needed:
                needed.append(field)
    missing = []
    for field in needed:
        value = state.get(field)
        if value is None or (field == "context" and not value):
            missing.append(field)
    return missing


def _step_ok(proposal: str, state: AgentState, allowed: set[str]) -> bool:
    """A proposal is acceptable only if it's a real, in-scope step whose
    data isn't collected yet AND that hasn't already failed this run.

    The failure check matters: retries live at the seam (bounded). The
    planner must never hammer a broken tool into a budget death-spiral —
    a failed step exits the plan, and the guard resolves the run.
    """
    if proposal not in NODE_REGISTRY:
        return proposal in ("report", "done")
    if proposal not in allowed:
        return False
    failed = {m["step"] for m in state["messages"]
              if m.get("step") and m.get("status") == "failed"}
    if NODE_REGISTRY[proposal]["fn"].__name__ in failed:
        return False
    field = NODE_REGISTRY[proposal]["data_field"]
    if field == "context":
        return not state["context"]  # "" = nothing retrieved yet
    return state.get(field) is None


def plan(state: AgentState) -> AgentState:
    """Planner node: propose the next step, validate it against the registry.

    LLM proposes; CODE decides. The accepted decision lands in
    state['next_step'] — the conditional edge below only READS state,
    it never re-asks the model.
    """
    if budget_guard(state):
        # Hard stop — and still produce an answer, typed, without
        # spending another token on an LLM call.
        if state["report"] is None:
            state["report"] = _blocked_answer(
                ["AGENT BUDGET EXCEEDED: step/cost ceiling reached before a "
                 "report was produced"],
                ["Raise MAX_STEPS/MAX_COST, or narrow the query"])
        state["next_step"] = "stop"
        _record(state, "plan", decision="stop", reason="budget exceeded")
        return state

    # Deterministic refusal — imperative action, before any LLM call.
    match = IMPERATIVE_ACTIONS.match(state["query"].lower())
    if match:
        state["next_step"] = "refuse"
        _record(state, "plan", proposal=match.group(1), decision="refuse",
                reason="imperative action — registry check before any LLM call")
        return state

    # Structural scope: which steps are worth proposing for THIS query?
    categories = classify_query(state["query"]).split("+")
    allowed = {FIELD_TO_STEP[f] for c in categories for f in REQUIREMENTS[c]} | {"retrieve"}

    proposal = router(state)
    known = set(NODE_REGISTRY) | {"report", "done"}

    if proposal not in known:
        # The model asked for a capability that does not exist → refuse.
        state["next_step"] = "refuse"
        _record(state, "plan", proposal=proposal, decision="refuse",
                reason="not in registry")
        return state

    if not _step_ok(proposal, state, allowed):
        # Either already collected (anti-cascade) or out of scope for
        # this query (anti-cascade-by-contract). Re-ask ONCE with the
        # correction; if the model can't course-correct, the GUARD
        # decides — never an unbounded loop, never the prompt alone.
        original = proposal
        retry = router(state, correction=(
            f"'{proposal}' is not appropriate right now — it is either already "
            "collected or not needed for this query type. Needed steps: "
            f"{', '.join(sorted(s for s in allowed if _step_ok(s, state, allowed))) or 'none'}"
            ". Propose one of those, or 'report'."
        ))
        if retry in known and _step_ok(retry, state, allowed):
            proposal = retry
            decision = "corrected"
        else:
            proposal = "report" if not _required_missing(state, categories) else "validate"
            decision = "fallback"
        state["next_step"] = proposal
        # proposal = what the model FIRST said; corrected_to = what the
        # code actually dispatched (or resolved to via fallback).
        _record(state, "plan", proposal=original, decision=decision,
                corrected_to=proposal)
        return state

    state["next_step"] = proposal
    _record(state, "plan", proposal=proposal, decision="accept")
    return state


def route_from_plan(state: AgentState) -> str:
    """The edge is a pure read — plan() already made the decision."""
    return state["next_step"]


def _blocked_answer(reasons: list[str], next_steps: list[str]) -> AgentAnswer:
    """The guard's output: a typed, deterministic answer — not prose."""
    return AgentAnswer(
        answer="Agent stopped before generating a report: " + "; ".join(reasons),
        verdict=ReadinessVerdict(
            ready=False,
            confidence="low",
            blockers=reasons,
            recommended_next_steps=next_steps,
        ),
    )


def validate(state: AgentState) -> AgentState:
    """Validity guard: is the state acceptable for THIS query's report?

    Checks required fields (derived from the query category) and hard
    facts (failing build). On failure it writes the blocked report
    itself — ready=False, typed, with reasons — and sets error.
    """
    category = classify_query(state["query"])          # label, e.g. "incidents+deploys"
    categories = category.split("+")
    reasons: list[str] = []
    next_steps: list[str] = []

    for field in _required_missing(state, categories):
        step = FIELD_TO_STEP.get(field, field)
        reasons.append(
            f"REQUIRED DATA MISSING: '{field}' was never collected "
            f"(step '{step}' skipped or failed)")
        next_steps.append(f"Run {step} before answering this query")

    build = state["build_status"]
    if build is not None and build.status == "down":
        since = f" since {build.failing_since}" if build.failing_since else ""
        reasons.append(f"BUILD FAILING: status 'down'{since}")
        next_steps.append("Fix the failing build before release")

    if reasons:
        state["error"] = f"guard ({category}): " + "; ".join(reasons)
        state["report"] = _blocked_answer(reasons, next_steps)
        _record(state, "validate", status="blocked", category=category)
    else:
        _record(state, "validate", status="passed", category=category)
    return state


def route_after_validate(state: AgentState) -> str:
    """Blocked = the guard already wrote the report → stop.
    Pass = no report yet → let the model generate one."""
    return "end" if state["report"] is not None else "generate_report"


def refuse(state: AgentState) -> AgentState:
    """Registry-driven refusal: no tool exists for what was asked.

    The message is CONSTRUCTED from the registry — the model never
    invents the list of what's available.
    """
    proposal = next(
        (m.get("proposal") for m in reversed(state["messages"])
         if m["step"] == "plan" and "proposal" in m),
        "unknown action",
    )
    available = ", ".join(NODE_REGISTRY)
    state["error"] = f"refused: no registered step for '{proposal}'"
    state["report"] = AgentAnswer(
        answer=(f"I can't do that — '{proposal}' is not an available action. "
                f"DevBuddy can: {available}."),
        verdict=ReadinessVerdict(
            ready=False,
            confidence="low",
            blockers=[f"Requested action '{proposal}' has no registered tool"],
            recommended_next_steps=[f"Ask for one of: {available}"],
        ),
    )
    _record(state, "refuse", action=proposal)
    return state


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
    Dynamic agent: plan → registry → act, in a loop.

    One planner node, ONE conditional edge (reading state), and every
    data node feeds back into the planner. The validity guard sits
    between 'report' and the model — nothing reaches generate_report
    without passing validate first.
    """
    graph = StateGraph(AgentState)
    graph.add_node("extract_service", extract_service)
    graph.add_node("plan", plan)
    graph.add_node("validate", validate)
    graph.add_node("refuse", refuse)
    graph.add_node("report", generate_report)

    for name, spec in NODE_REGISTRY.items():
        graph.add_node(name, spec["fn"])
        graph.add_edge(name, "plan")

    graph.set_entry_point("extract_service")
    graph.add_edge("extract_service", "plan")
    graph.add_conditional_edges("plan", route_from_plan, PLAN_ROUTE_MAP)
    graph.add_conditional_edges("validate", route_after_validate,
                                {"generate_report": "report", "end": END})
    graph.add_edge("refuse", END)
    graph.add_edge("report", END)
    return graph.compile()


def build_guarded_chain(include_build: bool = True) -> StateGraph:
    """
    C3: fixed chain + validity guard (conditional edge before report).

    include_build=False reproduces C2's missing-step graph WITH the
    guard attached — the guard catches what the missing node left
    behind, instead of letting the report fill the gap.
    """
    graph = StateGraph(AgentState)
    graph.add_node("extract_service", extract_service)
    graph.add_node("retrieve", retrieve_context)
    graph.add_node("check_build", check_build)
    graph.add_node("check_deploys", check_deploys)
    graph.add_node("validate", validate)
    graph.add_node("report", generate_report)

    graph.set_entry_point("extract_service")
    graph.add_edge("extract_service", "retrieve")
    if include_build:
        graph.add_edge("retrieve", "check_build")
        graph.add_edge("check_build", "check_deploys")
    else:
        graph.add_edge("retrieve", "check_deploys")
    graph.add_edge("check_deploys", "validate")
    graph.add_conditional_edges("validate", route_after_validate,
                                {"generate_report": "report", "end": END})
    graph.add_edge("report", END)
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


def build_missing_step_agent() -> StateGraph:
    """
    C2: the C1-style chain with check_build REMOVED and NO guard.

    state['build_status'] stays None all the way into the naive report
    node — which renders it as '{}' and lets the model fill the gap.
    That gap-filling IS the hallucination engineers must witness.
    """
    graph = StateGraph(AgentState)
    graph.add_node("extract_service", extract_service)
    graph.add_node("retrieve", retrieve_context)
    graph.add_node("check_deploys", check_deploys)
    graph.add_node("report", generate_report_naive)  # naive node, no validate
    graph.set_entry_point("extract_service")
    graph.add_edge("extract_service", "retrieve")
    graph.add_edge("retrieve", "check_deploys")
    graph.add_edge("check_deploys", "report")
    graph.add_edge("report", END)
    return graph.compile()


def run_guarded_chain(query: str, include_build: bool = True) -> dict:
    """Run the C3 guarded chain. include_build=False = C2's missing step."""
    agent = build_guarded_chain(include_build=include_build)
    return agent.invoke(_init_state(query))


def run_missing_step_agent(query: str) -> dict:
    """Run the C2 missing-step graph (no guard, naive report)."""
    agent = build_missing_step_agent()
    return agent.invoke(_init_state(query))