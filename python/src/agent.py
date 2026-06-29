"""
Week 6 — Agent Orchestrator: Multi-Step Workflows

Chains retrieval (Week 3), MCP tool calling (Week 5), and structured output
(Week 2) into an autonomous pipeline using LangGraph.

Imports:
  from src.llm import get_llm
  from src.rag import retrieve
  MCP session for tool calls
"""
import os, sys, json, asyncio
from typing import TypedDict

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.rag import retrieve


# ═══════════════════════════════════════════════════════════════
# Agent State — carried across all steps
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# MCP Session — persistent connection to the tool server
# ═══════════════════════════════════════════════════════════════

SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "mcp_server.py")
_mcp_session = None


def _get_mcp_session():
    """Return a persistent MCP session. Connects once, reused across calls."""
    global _mcp_session
    if _mcp_session is not None:
        return _mcp_session

    from mcp.client.stdio import stdio_client
    from mcp import ClientSession, StdioServerParameters

    params = StdioServerParameters(command="python", args=[SERVER_SCRIPT])
    _mcp_session = (stdio_client(params), None)  # placeholder
    return _mcp_session


def _call_mcp_tool(tool_name: str, args: dict) -> str:
    """Call a tool on the MCP server. Creates session on first call."""
    async def _call():
        from mcp.client.stdio import stdio_client
        from mcp import ClientSession, StdioServerParameters
        params = StdioServerParameters(command="python", args=[SERVER_SCRIPT])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, args)
                return result.content[0].text if result.content else "no result"
    return asyncio.run(_call())


# ═══════════════════════════════════════════════════════════════
# Agent State — carried across all steps
# ═══════════════════════════════════════════════════════════════

class AgentState(TypedDict):
    query: str
    service_name: str
    context: str
    build_status: str
    deploys: str
    incidents: str
    report: str
    steps: int
    cost: float


def _estimate_cost(response) -> float:
    """Estimate LLM call cost from usage metadata."""
    usage = response.usage_metadata or {}
    inp = usage.get("input_tokens", 0) if hasattr(usage, "get") else 0
    out = usage.get("output_tokens", 0) if hasattr(usage, "get") else 0
    return (inp * 0.15 + out * 0.60) / 1_000_000


# ═══════════════════════════════════════════════════════════════
# Nodes — each is one step in the workflow
# ═══════════════════════════════════════════════════════════════

def extract_service(state: AgentState) -> AgentState:
    """Extract the service name from the user's query."""
    if state.get("service_name"):
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
    return state


def retrieve_context(state: AgentState) -> AgentState:
    """Retrieve relevant documents from RAG."""
    chunks = retrieve(state["query"], k=3)
    state["context"] = "\n\n---\n\n".join(chunks)
    state["steps"] += 1
    return state


def _get_service(state: AgentState) -> str:
    """Get the service name from state. Fails if not set."""
    svc = state.get("service_name", "").strip()
    if not svc:
        raise RuntimeError("service_name not set — extract_service must run first")
    return svc


def check_build(state: AgentState) -> AgentState:
    """Call get_build_status via MCP server."""
    result = _call_mcp_tool("get_build_status", {"service_name": _get_service(state)})
    state["build_status"] = result
    state["steps"] += 1
    return state


def check_deploys(state: AgentState) -> AgentState:
    """Call get_recent_deploys via MCP server."""
    result = _call_mcp_tool("get_recent_deploys", {
        "service_name": _get_service(state), "limit": 3
    })
    state["deploys"] = result
    state["steps"] += 1
    return state


def check_incidents(state: AgentState) -> AgentState:
    """Call get_active_incidents via MCP server."""
    result = _call_mcp_tool("get_active_incidents", {"service_name": _get_service(state)})
    state["incidents"] = result
    state["steps"] += 1
    return state


def generate_report(state: AgentState) -> AgentState:
    """Produce a structured readiness report from all collected data."""
    llm = get_llm(temperature=0)

    # Build data section headers based on what was actually collected
    sections = ["Summary — one sentence answering the user's query"]
    data_parts = [f"Query: {state['query']}"]

    if state["context"]:
        sections.append("Relevant Documentation")
        data_parts.append(f"Relevant docs:\n{state['context']}")
    if state["build_status"]:
        sections.append("Build Status")
        data_parts.append(f"Build status: {state['build_status']}")
    if state["deploys"]:
        sections.append("Recent Deployments")
        data_parts.append(f"Recent deployments: {state['deploys']}")
    if state["incidents"]:
        sections.append("Active Incidents")
        data_parts.append(f"Active incidents: {state['incidents']}")

    section_list = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sections))
    data_text = "\n\n".join(data_parts)

    response = llm.invoke([
        SystemMessage(content=(
            "You are a site reliability engineer. Answer the user's query "
            "using ONLY the data provided. Do not invent information. "
            "Do not mention sections where no data was collected.\n\n"
            f"Include these sections:\n{section_list}"
        )),
        HumanMessage(content=data_text),
    ])

    state["report"] = response.content
    state["steps"] += 1
    state["cost"] += _estimate_cost(response)
    return state


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
    Fixed 3-step chain: extract → retrieve → build → report.
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
    graph.add_conditional_edges("retrieve", guard, {
        "retrieve": "retrieve",
        "check_build": "check_build",
        "check_deploys": "check_deploys",
        "check_incidents": "check_incidents",
        "report": "report",
        "done": END,
    })
    graph.add_conditional_edges("check_build", guard, {
        "retrieve": "retrieve",
        "check_build": "check_build",
        "check_deploys": "check_deploys",
        "check_incidents": "check_incidents",
        "report": "report",
        "done": END,
    })
    graph.add_conditional_edges("check_deploys", guard, {
        "retrieve": "retrieve",
        "check_build": "check_build",
        "check_deploys": "check_deploys",
        "check_incidents": "check_incidents",
        "report": "report",
        "done": END,
    })
    graph.add_conditional_edges("check_incidents", guard, {
        "retrieve": "retrieve",
        "check_build": "check_build",
        "check_deploys": "check_deploys",
        "check_incidents": "check_incidents",
        "report": "report",
        "done": END,
    })

    return graph.compile()


# ═══════════════════════════════════════════════════════════════
# Convenience function
# ═══════════════════════════════════════════════════════════════

def run_fixed_chain(query: str) -> dict:
    """Run the fixed 3-step chain and return the result."""
    from src.rag import index_documents
    index_documents(chunk_size=512)
    agent = build_fixed_chain()
    return agent.invoke({
        "query": query,
        "service_name": "",
        "context": "",
        "build_status": "",
        "deploys": "",
        "incidents": "",
        "report": "",
        "steps": 0,
        "cost": 0.0,
    })


def run_dynamic_agent(query: str) -> dict:
    """Run the dynamic agent and return the result with routing trace."""
    from src.rag import index_documents
    index_documents(chunk_size=512)
    agent = build_dynamic_agent()
    return agent.invoke({
        "query": query,
        "service_name": "",
        "context": "",
        "build_status": "",
        "deploys": "",
        "incidents": "",
        "report": "",
        "steps": 0,
        "cost": 0.0,
    })
