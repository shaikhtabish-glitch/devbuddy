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
    check_deploys, check_incidents, generate_report, router,
    budget_guard, plan, validate, route_after_validate, refuse,
    classify_query, NODE_REGISTRY, PLAN_ROUTE_MAP, REQUIREMENTS,
    build_fixed_chain, build_dynamic_agent, build_guarded_chain,
    run_fixed_chain, run_dynamic_agent, run_guarded_chain, _init_state,
    call_tool, ToolFailure,
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
    assert state["next_step"] == ""
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
# The seam — call_tool with pluggable backends
# ═══════════════════════════════════════════════════════════════

def test_seam_local_backend_returns_contract(monkeypatch):
    """Same tool name, no server: Week 4's in-process tools behind the seam."""
    monkeypatch.setenv("TOOL_BACKEND", "local")
    result = call_tool("get_build_status", {"service_name": "payment-api"},
                       contract=BuildStatus)
    assert isinstance(result, BuildStatus)
    assert result.status == "degraded"  # W4 mock data — deterministic


def test_seam_local_backend_unknown_tool_fails_structured(monkeypatch):
    """No tool registered → ToolFailure with the registry in the message,
    not a crash and not a silent None."""
    monkeypatch.setenv("TOOL_BACKEND", "local")
    with pytest.raises(ToolFailure) as exc:
        call_tool("deploy_service", {"service_name": "payment-api"})
    assert "deploy_service" in str(exc.value)
    assert "available_tools" in str(exc.value) or "Unknown tool" in str(exc.value)


def test_seam_contract_violation_is_retried_then_fails(monkeypatch):
    """A result that violates the contract is a RETRYABLE failure —
    transport errors and schema violations share one policy."""
    monkeypatch.setenv("TOOL_BACKEND", "local")
    with pytest.raises(ToolFailure) as exc:
        # build-status output will never satisfy the Incident contract
        call_tool("get_build_status", {"service_name": "payment-api"},
                  contract=Incident)
    assert "attempt" in str(exc.value)


def test_seam_local_backend_validates_lists(monkeypatch):
    monkeypatch.setenv("TOOL_BACKEND", "local")
    result = call_tool("get_recent_deploys", {"service_name": "auth-service"},
                       contract=DeployRecord, many=True)
    assert isinstance(result, list)
    assert all(isinstance(d, DeployRecord) for d in result)


@needs_qdrant
def test_fixed_chain_runs_local_backend(_index_ready, monkeypatch):
    """End-to-end with the wire swapped: same agent, zero MCP server."""
    monkeypatch.setenv("TOOL_BACKEND", "local")
    result = run_fixed_chain("Is payment-api healthy?")
    assert isinstance(result["report"], AgentAnswer)
    assert result["error"] == "", result["error"]
    assert result["build_status"].status == "degraded"
    assert result["steps"] == 4


# ═══════════════════════════════════════════════════════════════
# Registry + classification — the structural layer (pure, no LLM)
# ═══════════════════════════════════════════════════════════════

def test_classify_query_categories():
    assert classify_query("Is payment-api ready for v2.1?") == "readiness"
    assert classify_query("Is payment-api healthy?") == "health"
    assert classify_query("What was deployed recently?") == "deploys"
    assert classify_query("Any incidents for inventory-service?") == "incidents"
    assert classify_query("What does the payment-api spec say?") == "docs"
    assert classify_query("Deploy auth-service to production") == "action"
    assert classify_query("Give me a full readiness assessment") == "full"
    assert classify_query("hello") == "general"


def test_registry_drives_router_catalog_and_route_map():
    """One source of truth: the prompt's step list and the graph's edge
    map both derive from NODE_REGISTRY — they cannot drift."""
    from src.agent import _router_catalog
    catalog = _router_catalog()
    for name in NODE_REGISTRY:
        assert f"- {name}:" in catalog
    # every registry step is routable, plus report/done/refuse/stop
    assert set(PLAN_ROUTE_MAP) == set(NODE_REGISTRY) | {"report", "refuse", "done", "stop"}
    assert PLAN_ROUTE_MAP["report"] == "validate"
    assert PLAN_ROUTE_MAP["done"] == "validate"  # "wrap up" → guard decides
    # every requirement names a real state field with a real step
    for fields in REQUIREMENTS.values():
        for field in fields:
            assert field in ("context", "build_status", "deploys", "incidents")


# ═══════════════════════════════════════════════════════════════
# The three guards (pure logic — no LLM, no services)
# ═══════════════════════════════════════════════════════════════

def test_budget_guard_trips_on_steps():
    state = _init_service_state()
    assert budget_guard(state) is False
    state["steps"] = MAX_STEPS
    assert budget_guard(state) is True


def test_budget_guard_trips_on_cost():
    state = _init_service_state()
    state["cost"] = MAX_COST
    assert budget_guard(state) is True


def test_validate_blocks_when_required_build_missing():
    """C3: readiness query, build never checked → guard STOPS the agent
    and writes the blocked report itself — typed, deterministic."""
    state = _init_service_state("Is payment-api ready for v2.1?")
    state = validate(state)
    assert state["report"] is not None
    assert state["report"].verdict.ready is False
    assert any("build_status" in b for b in state["report"].verdict.blockers)
    assert state["error"].startswith("guard (readiness)")
    assert route_after_validate(state) == "end"


def test_validate_passes_when_required_data_present():
    state = _init_service_state("Is payment-api healthy?")
    state["build_status"] = BuildStatus(status="healthy",
                                        last_deploy="2026-06-28T08:15:00Z")
    state = validate(state)
    assert state["report"] is None
    assert state["error"] == ""
    assert route_after_validate(state) == "generate_report"


def test_validate_blocks_on_failing_build():
    """Data present but DOWN → still blocked. The guard checks facts,
    not just presence."""
    state = _init_service_state("Is payment-api ready for release?")
    state["build_status"] = BuildStatus(status="down",
                                        last_deploy="2026-06-28T08:15:00Z",
                                        failing_since="2026-06-28T09:00:00Z")
    state["deploys"] = []
    state = validate(state)
    assert state["report"].verdict.ready is False
    assert any("BUILD FAILING" in b for b in state["report"].verdict.blockers)


def test_validate_blocks_docs_query_without_context():
    state = _init_service_state("What does the payment-api spec say?")
    state["context"] = ""  # retrieval failed / never ran
    state = validate(state)
    assert state["report"].verdict.ready is False
    assert any("context" in b for b in state["report"].verdict.blockers)


def test_refusal_message_is_built_from_registry():
    """Refusal is constructed from NODE_REGISTRY — the model never
    invents the list of available capabilities."""
    state = _init_service_state("Deploy auth-service to production")
    state["messages"].append({"step": "plan", "proposal": "deploy",
                              "decision": "refuse"})
    state = refuse(state)
    assert state["report"].verdict.ready is False
    assert "deploy" in state["report"].answer
    for name in NODE_REGISTRY:
        assert name in state["report"].answer or name in \
            state["report"].verdict.recommended_next_steps[0]
    assert state["error"].startswith("refused")


def test_guarded_chain_compiles_both_variants():
    assert build_guarded_chain() is not None
    assert build_guarded_chain(include_build=False) is not None


def test_refusal_end_to_end():
    """'Deploy …' must be refused structurally — the deterministic
    imperative check fires before any LLM routing call. Needs only the
    LLM (service extraction), no MCP server, no Qdrant."""
    result = run_dynamic_agent("Deploy auth-service to production")
    assert result["next_step"] == "refuse"
    assert result["error"].startswith("refused")
    assert result["report"].verdict.ready is False
    assert "check_build" in result["report"].answer  # registry listed


# ═══════════════════════════════════════════════════════════════
# Router
# ═══════════════════════════════════════════════════════════════

def test_router_returns_valid_step():
    state = _init_service_state()
    decision = router(state)
    assert decision in set(NODE_REGISTRY) | {"report", "done"}


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


@needs_mcp
def test_guarded_chain_passes_with_build(_index_ready):
    """C3 test 1: required data present → guard passes → report generated."""
    result = run_guarded_chain("Is payment-api healthy?")
    assert result["build_status"] is not None
    assert isinstance(result["report"], AgentAnswer)
    assert result["error"] == "", result["error"]
    assert any(m["step"] == "validate" and m["status"] == "passed"
               for m in result["messages"])


@needs_mcp
def test_guarded_chain_blocks_when_check_build_removed(_index_ready):
    """C3 test 2: the C2 missing-step graph WITH the guard → the guard
    stops the agent instead of letting the report invent build data."""
    result = run_guarded_chain("Is payment-api healthy?", include_build=False)
    assert result["build_status"] is None
    assert result["error"].startswith("guard (health)")
    assert result["report"].verdict.ready is False
    assert any("build_status" in b for b in result["report"].verdict.blockers)
    # no LLM-generated report happened — the guard wrote a typed one
    assert not any(m["step"] == "generate_report" for m in result["messages"])


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _init_service_state(query: str = "Is payment-api healthy?") -> AgentState:
    state = _init_state(query)
    state["service_name"] = "payment-api"
    return state


def _init_context_state() -> AgentState:
    return _init_state("What does the payment-api spec say?")