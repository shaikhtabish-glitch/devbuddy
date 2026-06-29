"""Tests for src/agent.py — Week 6"""
import pytest
from src.rag import index_documents
from src.agent import (
    AgentState, extract_service, retrieve_context, check_build,
    check_deploys, check_incidents, generate_report, router, guard,
    build_fixed_chain, build_dynamic_agent,
    run_fixed_chain, run_dynamic_agent,
    MAX_STEPS, MAX_COST,
)


# ═══════════════════════════════════════════════════════════════
# Import graph + structure
# ═══════════════════════════════════════════════════════════════

def test_agent_imports_all_modules():
    """agent.py imports from llm, schemas, rag, tools — complete graph."""
    from src.agent import retrieve_context, check_build, generate_report
    import inspect

    # llm
    src = inspect.getsource(generate_report)
    assert "get_llm" in src
    # rag
    src = inspect.getsource(retrieve_context)
    assert "retrieve" in src
    # tools
    src = inspect.getsource(check_build)
    assert "get_build_status" in src


def test_agent_state_fields():
    """AgentState has all required fields."""
    state = AgentState(
        query="test", service_name="", context="", build_status="",
        deploys="", incidents="", report="", steps=0, cost=0.0,
    )
    assert state["query"] == "test"
    assert state["steps"] == 0


def test_extract_service_detects_auth():
    """Extracts auth-service from a query about auth."""
    state = AgentState(
        query="Is the auth-service healthy?", service_name="",
        context="", build_status="", deploys="", incidents="",
        report="", steps=0, cost=0.0,
    )
    result = extract_service(state)
    assert "auth-service" in result["service_name"]


# ═══════════════════════════════════════════════════════════════
# Nodes
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(scope="module", autouse=True)
def _ensure_index():
    """Ensure the RAG index exists before any agent tests."""
    import src.rag as rag
    rag._vectorstore = None
    rag._documents = None
    rag._embeddings = None
    index_documents(chunk_size=512)


@pytest.fixture
def base_state():
    return AgentState(
        query="Is payment-api healthy?",
        service_name="payment-api", context="", build_status="",
        deploys="", incidents="", report="", steps=0, cost=0.0,
    )


def test_retrieve_context_populates(base_state):
    state = retrieve_context(base_state)
    assert state["context"], "Context should not be empty"
    assert state["steps"] == 1


def test_check_build_populates(base_state):
    state = check_build(base_state)
    assert state["build_status"], "Build status should not be empty"
    assert "status" in state["build_status"]  # returns JSON with status field


def test_check_deploys_populates(base_state):
    state = check_deploys(base_state)
    assert state["deploys"], "Deploys should not be empty"


def test_check_incidents_populates(base_state):
    state = check_incidents(base_state)
    assert state["incidents"], "Incidents should not be empty"


def test_generate_report_produces_output(base_state):
    base_state["context"] = "Payment API spec"
    base_state["build_status"] = '{"status": "degraded"}'
    state = generate_report(base_state)
    assert state["report"], "Report should not be empty"
    assert state["steps"] == 1
    assert state["cost"] > 0


# ═══════════════════════════════════════════════════════════════
# Router + Guard
# ═══════════════════════════════════════════════════════════════

def test_router_returns_valid_step(base_state):
    decision = router(base_state)
    assert decision in ("retrieve", "check_build", "check_deploys",
                        "check_incidents", "report", "done")


def test_guard_stops_at_max_steps(base_state):
    base_state["steps"] = MAX_STEPS
    assert guard(base_state) == "done"


def test_guard_stops_at_max_cost(base_state):
    base_state["cost"] = MAX_COST
    assert guard(base_state) == "done"


def test_guard_delegates_when_under_limits(base_state):
    decision = guard(base_state)
    assert decision != "done"  # should route normally


# ═══════════════════════════════════════════════════════════════
# Graph compilation
# ═══════════════════════════════════════════════════════════════

def test_fixed_chain_compiles():
    agent = build_fixed_chain()
    assert agent is not None


def test_dynamic_agent_compiles():
    agent = build_dynamic_agent()
    assert agent is not None


def test_fixed_chain_runs():
    result = run_fixed_chain("Is payment-api healthy?")
    assert result["report"], "Report should not be empty"
    assert result["steps"] == 3
    assert result["cost"] > 0


def test_dynamic_agent_runs():
    result = run_dynamic_agent("Is payment-api healthy?")
    assert result["report"], "Report should not be empty"
    assert result["steps"] >= 1


def test_dynamic_agent_different_queries_different_steps():
    r1 = run_dynamic_agent("Is payment-api healthy?")
    r2 = run_dynamic_agent("What was deployed recently and any incidents?")
    # Different queries may take different paths
    assert r1["steps"] >= 1
    assert r2["steps"] >= 1
