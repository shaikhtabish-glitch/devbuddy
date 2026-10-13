"""Tests for src/agent.py — Week 6

Two tiers:
  - Unit tests: pure state/graph/contract logic — run anywhere.
  - Integration tests: marked skipif against live Qdrant (6333) and the
    MCP server (8000). The documented readiness command therefore works
    in a clean checkout and says exactly what it couldn't verify.
"""
import ast
import inspect
import socket

import pytest
from pydantic import ValidationError

from src.rag import index_documents
from src.schemas import AgentAnswer, BuildStatus, DeployRecord, Incident, ReadinessVerdict
from src.agent import (
    AgentState, extract_service, retrieve_context, check_build,
    check_deploys, check_incidents, generate_report, router, guard,
    build_fixed_chain, build_dynamic_agent,
    run_fixed_chain, run_dynamic_agent, _init_state,
    MAX_STEPS, MAX_COST,
)


# ═══════════════════════════════════════════════════════════════
# Service availability — integration tests skip cleanly if down
# ═══════════════════════════════════════════════════════════════

def _port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


QDRANT_UP = _port_open(6333)
MCP_UP = _port_open(8000)

needs_qdrant = pytest.mark.skipif(
    not QDRANT_UP, reason="Qdrant not running — docker-compose up -d")
needs_mcp = pytest.mark.skipif(
    not MCP_UP, reason="MCP server not running — python src/mcp_server.py")


# ═══════════════════════════════════════════════════════════════
# Composition — the agent imports the modules YOU built
# ═══════════════════════════════════════════════════════════════

def test_agent_imports_its_own_modules():
    """agent.py composes Week 1 (llm), Week 2 (schemas), Week 3 (rag).

    Checked against the AST (what it actually imports) AND the body
    (what it actually uses) — not a substring guess.
    """
    import src.agent as agent_mod

    tree = ast.parse(inspect.getsource(agent_mod))
    imported = {
        node.module for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "src.llm" in imported, "Week 1: provider must be imported"
    assert "src.schemas" in imported, "Week 2: contracts must be imported"
    assert "src.rag" in imported, "Week 3: retrieval must be imported"

    src = inspect.getsource(agent_mod)
    assert "get_llm(" in src, "llm import must be used"
    assert "with_structured_output(AgentAnswer)" in src, \
        "schemas import must be used — structured output is the Week 2 payoff"
    assert "retrieve(" in src, "rag import must be used"


def test_agent_state_is_fully_typed():
    """Every data field is a contract (or None), plus error + audit trail."""
    hints = AgentState.__annotations__
    assert hints["build_status"] == "BuildStatus | None" or "BuildStatus" in str(hints["build_status"])
    assert "DeployRecord" in str(hints["deploys"])
    assert "Incident" in str(hints["incidents"])
    assert "AgentAnswer" in str(hints["report"])
    assert hints["error"] is str
    assert "messages" in hints


def test_init_state_defaults():
    state = _init_state("test query")
    assert state["query"] == "test query"
    assert state["build_status"] is None
    assert state["deploys"] is None
    assert state["incidents"] is None
    assert state["report"] is None
    assert state["steps"] == 0
    assert state["cost"] == 0.0
    assert state["error"] == ""
    assert state["messages"] == []


def test_report_contract_rejects_contradiction():
    """Week 2 validators run on the agent's output: ready=True + blockers dies."""
    with pytest.raises(ValidationError):
        AgentAnswer(
            answer="looks good",
            verdict=ReadinessVerdict(ready=True, confidence="high",
                                     blockers=["but there is a blocker"]),
        )


def test_blocked_report_contract_is_constructible():
    """The guard-shaped answer (ready=False, blockers, no evidence) validates."""
    answer = AgentAnswer(
        answer="Release blocked.",
        verdict=ReadinessVerdict(
            ready=False, confidence="low",
            blockers=["BUILD STATUS UNKNOWN — check was skipped or failed"],
            recommended_next_steps=["Run check_build before attempting release"],
        ),
    )
    assert answer.verdict.ready is False


# ═══════════════════════════════════════════════════════════════
# Nodes
# ═══════════════════════════════════════════════════════════════

def test_extract_service_detects_auth():
    state = _init_state("Is the auth-service healthy?")
    result = extract_service(state)
    assert "auth-service" in result["service_name"]
    assert result["steps"] == 1
    # audit trail records the step
    assert result["messages"][-1]["step"] == "extract_service"
    assert result["messages"][-1]["service"] == "auth-service"


@pytest.fixture(scope="module")
def _index_ready():
    """Reset the in-process RAG state and (re)build the index.

    Non-autouse on purpose: unit tests must keep running when Qdrant is down.
    """
    if not QDRANT_UP:
        pytest.skip("Qdrant not running — docker-compose up -d")
    import src.rag as rag
    rag._vectorstore = None
    rag._documents = None
    rag._embeddings = None
    index_documents(chunk_size=512)


def test_retrieve_context_populates(_index_ready):
    state = _init_context_state()
    state = retrieve_context(state)
    assert state["context"], "Context should not be empty"
    assert state["steps"] == 1
    assert state["error"] == ""
    assert state["messages"][-1]["step"] == "retrieve_context"


@needs_mcp
def test_check_build_returns_contract():
    state = _init_service_state()
    state = check_build(state)
    assert state["error"] == "", state["error"]
    assert isinstance(state["build_status"], BuildStatus)
    assert state["build_status"].status in ("healthy", "degraded", "down", "unknown")
    assert state["messages"][-1]["step"] == "check_build"


@needs_mcp
def test_check_deploys_returns_contracts():
    state = _init_service_state()
    state = check_deploys(state)
    assert state["error"] == "", state["error"]
    assert isinstance(state["deploys"], list)
    assert all(isinstance(d, DeployRecord) for d in state["deploys"])


@needs_mcp
def test_check_incidents_returns_contracts():
    state = _init_service_state()
    state = check_incidents(state)
    assert state["error"] == "", state["error"]
    assert isinstance(state["incidents"], list)
    assert all(isinstance(i, Incident) for i in state["incidents"])


def test_generate_report_returns_structured_answer():
    state = _init_service_state()
    state["context"] = "Payment API spec: processes transactions."
    state["build_status"] = BuildStatus(status="healthy",
                                        last_deploy="2026-06-28T08:15:00Z")
    state = generate_report(state)
    assert isinstance(state["report"], AgentAnswer)
    assert state["report"].answer
    assert state["steps"] == 1
    assert state["cost"] >= 0
    if state["error"]:
        # a contract rejection is surfaced, never hidden — but it should be rare
        pytest.fail(f"report contract rejected model output: {state['error']}")


def test_unchecked_fields_render_as_not_checked():
    """None means NOT CHECKED — and the prompt says so, in caps.

    This is the defense half of C2: the naive report node (demo-04)
    renders empty state as '{}' and the model invents data; this
    rendering tells the model the truth instead.
    """
    from src.agent import _data_section
    assert "NOT CHECKED" in _data_section("Build status", None)
    build = BuildStatus(status="healthy", last_deploy="2026-06-28T08:15:00Z")
    rendered = _data_section("Build status", build)
    assert "NOT CHECKED" not in rendered
    assert "healthy" in rendered


def test_generate_report_runs_with_missing_fields():
    state = _init_service_state()
    state["context"] = "auth-service spec."
    # build_status / deploys / incidents deliberately left None
    state = generate_report(state)
    assert isinstance(state["report"], AgentAnswer)
    assert state["report"].answer
    assert state["error"] == "", state["error"]


# ═══════════════════════════════════════════════════════════════
# Router + Guard
# ═══════════════════════════════════════════════════════════════

def test_router_returns_valid_step():
    state = _init_service_state()
    decision = router(state)
    assert decision in ("retrieve", "check_build", "check_deploys",
                        "check_incidents", "report", "done")


def test_guard_stops_at_max_steps():
    state = _init_service_state()
    state["steps"] = MAX_STEPS
    assert guard(state) == "done"


def test_guard_stops_at_max_cost():
    state = _init_service_state()
    state["cost"] = MAX_COST
    assert guard(state) == "done"


def test_guard_delegates_when_under_limits():
    state = _init_service_state()
    decision = guard(state)
    assert decision != "done"  # should route normally


# ═══════════════════════════════════════════════════════════════
# Graph compilation + end-to-end
# ═══════════════════════════════════════════════════════════════

def test_fixed_chain_compiles():
    assert build_fixed_chain() is not None


def test_dynamic_agent_compiles():
    assert build_dynamic_agent() is not None


@needs_mcp
def test_fixed_chain_runs(_index_ready):
    result = run_fixed_chain("Is payment-api healthy?")
    assert isinstance(result["report"], AgentAnswer)
    assert result["report"].answer
    assert result["steps"] == 4, \
        "fixed chain = extract + retrieve + check_build + report"
    assert result["cost"] > 0
    assert result["error"] == ""
    # audit trail tells the story — nothing reconstructed
    assert [m["step"] for m in result["messages"]] == [
        "extract_service", "retrieve_context", "check_build", "generate_report",
    ]


@needs_mcp
def test_dynamic_agent_runs(_index_ready):
    result = run_dynamic_agent("Is payment-api healthy?")
    assert isinstance(result["report"], AgentAnswer)
    assert result["report"].answer
    assert result["steps"] >= 1
    assert result["messages"], "audit trail must record the path taken"


@needs_mcp
def test_dynamic_agent_handles_different_queries(_index_ready):
    r1 = run_dynamic_agent("Is payment-api healthy?")
    r2 = run_dynamic_agent("What was deployed recently for auth-service?")
    for r in (r1, r2):
        assert isinstance(r["report"], AgentAnswer)
        assert r["report"].answer
        assert r["messages"]


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _init_service_state(query: str = "Is payment-api healthy?") -> AgentState:
    state = _init_state(query)
    state["service_name"] = "payment-api"
    return state


def _init_context_state() -> AgentState:
    return _init_state("What does the payment-api spec say?")