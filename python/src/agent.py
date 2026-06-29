"""
Week 6 — Agent Orchestrator: Multi-Step Workflows

Chains retrieval (Week 3), tool calling (Week 4), and structured output
(Week 2) into an autonomous pipeline using LangGraph.

Imports:
  from src.llm import get_llm
  from src.schemas import ServiceReadinessReport
  from src.rag import retrieve
  from src.tools import get_build_status, get_recent_deploys, get_active_incidents
"""
import json
from typing import TypedDict

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.rag import retrieve
from src.tools import (
    get_build_status, get_recent_deploys, get_active_incidents,
    execute_tool_safely, ALL_TOOLS,
)


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


def check_build(state: AgentState) -> AgentState:
    """Call get_build_status for the service named in the query."""
    svc = state.get("service_name", "payment-api")
    result = get_build_status.invoke({"service_name": svc})
    state["build_status"] = result
    state["steps"] += 1
    return state


def check_deploys(state: AgentState) -> AgentState:
    """Call get_recent_deploys for the service named in the query."""
    svc = state.get("service_name", "payment-api")
    result = get_recent_deploys.invoke({"service_name": svc, "limit": 3})
    state["deploys"] = result
    state["steps"] += 1
    return state


def check_incidents(state: AgentState) -> AgentState:
    """Call get_active_incidents for the service named in the query."""
    svc = state.get("service_name", "payment-api")
    result = get_active_incidents.invoke({"service_name": svc})
    state["incidents"] = result
    state["steps"] += 1
    return state


def generate_report(state: AgentState) -> AgentState:
    """Produce a structured readiness report from all collected data."""
    llm = get_llm(temperature=0)

    response = llm.invoke([
        SystemMessage(content=(
            "You are a site reliability engineer. Produce a service readiness report. "
            "Use ONLY the data provided. If data is missing, note it as 'unknown'. "
            "Do not invent information.\n\n"
            "Format your report with these sections:\n"
            "1. Summary — one sentence about the service state\n"
            "2. Build Status — current health\n"
            "3. Recent Deployments — what was deployed and when\n"
            "4. Active Incidents — any ongoing issues\n"
            "5. Readiness Verdict — READY or BLOCKED with specific reasons\n"
            "6. Recommended Actions — what to do next"
        )),
        HumanMessage(content=(
            f"Query: {state['query']}\n\n"
            f"Relevant documentation:\n{state['context'] or '(none)'}\n\n"
            f"Build status: {state['build_status'] or '(not checked)'}\n\n"
            f"Recent deployments: {state['deploys'] or '(not checked)'}\n\n"
            f"Active incidents: {state['incidents'] or '(not checked)'}"
        )),
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
            "- retrieve   (if the query needs documentation context)\n"
            "- check_build   (if build/health status is needed)\n"
            "- check_deploys (if deployment history is needed)\n"
            "- check_incidents (if incident data is needed)\n"
            "- report    (if all needed data has been collected, generate the final report)\n"
            "- done      (if the task is complete or cannot proceed)\n\n"
            "Choose the FIRST unmet need. Do not repeat steps that have data already."
        )),
        HumanMessage(content=(
            f"QUERY: {state['query']}\n\n"
            f"CURRENT STATE:\n"
            f"- Steps completed: {state['steps']}\n"
            f"- Context retrieved: {'YES' if state['context'] else 'NO'}\n"
            f"- Build status checked: {'YES' if state['build_status'] else 'NO'}\n"
            f"- Deploys checked: {'YES' if state['deploys'] else 'NO'}\n"
            f"- Incidents checked: {'YES' if state['incidents'] else 'NO'}\n\n"
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
    """Stop the agent if step count or cost exceeds limits."""
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
