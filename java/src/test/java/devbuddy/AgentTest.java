package devbuddy;

import devbuddy.agent.*;
import devbuddy.agent.ToolBackend;
import devbuddy.schemas.EvidenceChunk;
import devbuddy.schemas.ReadinessVerdict;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Week 6 — agent architecture tests (pure: no MCP server, no Qdrant, no LLM).
 *
 * <p>Mirrors the composition/unit portions of {@code tests/test_agent.py} /
 * {@code tests/test_agent.js}: source-composition checks document the
 * architecture, the rest are guard/registry/classifier units.</p>
 *
 * <p>Run: {@code mvn test -Dtest=AgentTest}</p>
 * <p>LLM + integration flows live in {@link AgentLlmTest}.</p>
 */
class AgentTest {

    // ─── Composition: the architecture is enforced in code ──────

    private static String source(String file) throws Exception {
        return Files.readString(Path.of("src/main/java/devbuddy/agent/" + file));
    }

    @Test
    @DisplayName("registry is the single source of truth (4 surfaces generated from it)")
    void registryDrivesAllSurfaces() throws Exception {
        String registry = source("Registry.java");
        // the router catalog, route map, requirements and refusal all READ it
        assertTrue(registry.contains("NODE_REGISTRY.forEach((name, spec) ->\n                sb.append"),
                "router catalog must be generated from NODE_REGISTRY");
        assertTrue(registry.contains("NODE_REGISTRY.forEach((name, spec) -> PLAN_ROUTE_MAP.put"),
                "PLAN_ROUTE_MAP must be generated from NODE_REGISTRY");
        assertTrue(registry.contains("return String.join(\", \", NODE_REGISTRY.keySet())"),
                "refusal message must be constructed from the registry");
        assertTrue(registry.contains("REQUIREMENTS = Map.of("),
                "guard requirements live beside the registry");
    }

    @Test
    @DisplayName("guards write typed blocked answers in CODE — no LLM call")
    void guardsWriteBlockedAnswersInCode() throws Exception {
        String guards = source("Guards.java");
        assertTrue(guards.contains("state.report = blockedAnswer(reasons, nextSteps)"),
                "validate must write the blocked report itself");
        assertTrue(guards.contains("state.record(\"validate\", AgentState.detail(\"status\", \"blocked\""),
                "validate must record its decision in the audit trail");
        assertTrue(guards.contains("Registry.refusalList()"),
                "refusal message must be registry-driven");
    }

    @Test
    @DisplayName("planner checks the budget and refuses imperatives pre-LLM")
    void plannerChecksBudgetAndImperativesFirst() throws Exception {
        String planner = source("Planner.java");
        assertTrue(planner.contains("if (Budget.exceeded(state))"),
                "plan must consult the budget before proposing");
        int budgetCheck = planner.indexOf("Budget.exceeded(state)");
        int imperativeCheck = planner.indexOf("IMPERATIVE_ACTIONS.matcher");
        int routerCall = planner.indexOf("router(state, null)");
        assertTrue(budgetCheck < routerCall && imperativeCheck < routerCall,
                "budget + imperative checks must run BEFORE the first LLM call");
    }

    // ─── AgentAnswer contract (Week 2 validators on Week 6 output) ──

    @Test
    @DisplayName("AgentAnswer rejects ready=true with blockers")
    void agentAnswerRejectsReadyWithBlockers() {
        assertThrows(IllegalArgumentException.class, () -> new AgentAnswer(
                "ready!", new ReadinessVerdict(true, ReadinessVerdict.Confidence.HIGH,
                        List.of("but blockers"), List.of()), List.of()));
    }

    @Test
    @DisplayName("AgentAnswer rejects not-ready with high confidence and no blockers")
    void agentAnswerRejectsNotReadyHighWithoutBlockers() {
        assertThrows(IllegalArgumentException.class, () -> new AgentAnswer(
                "not ready", new ReadinessVerdict(false, ReadinessVerdict.Confidence.HIGH,
                        List.of(), List.of()), List.of()));
    }

    @Test
    @DisplayName("AgentAnswer accepts verdict=null (docs-style answers)")
    void agentAnswerAcceptsNullVerdict() {
        AgentAnswer a = AgentAnswer.of("The SLA is 99.95%.");
        assertNull(a.verdict());
        assertTrue(a.evidence().isEmpty());
    }

    // ─── State defaults ─────────────────────────────────────────

    @Test
    @DisplayName("new state starts empty — empty means NOT CHECKED yet")
    void stateDefaultsAreEmpty() {
        AgentState state = new AgentState("Is payment-api healthy?");
        assertEquals("Is payment-api healthy?", state.query);
        assertEquals("", state.serviceName);
        assertEquals("", state.context);
        assertEquals("", state.buildStatus);
        assertEquals("", state.deploys);
        assertEquals("", state.incidents);
        assertNull(state.report);
        assertEquals(0, state.steps);
        assertEquals(0.0, state.cost);
        assertEquals("", state.error);
        assertTrue(state.messages.isEmpty());
    }

    // ─── classifyQuery — deterministic categories, code not prompt ──

    @Test
    @DisplayName("classify: imperative → action")
    void classifyAction() {
        assertEquals("action", Registry.classifyQuery("Deploy auth-service to production"));
        assertEquals("action", Registry.classifyQuery("Rollback the payment-api release"));
    }

    @Test
    @DisplayName("classify: health / readiness / full")
    void classifyHealthReadinessFull() {
        assertEquals("health", Registry.classifyQuery("Is payment-api healthy?"));
        assertEquals("readiness", Registry.classifyQuery("Is it ready for release?"));
        assertEquals("full", Registry.classifyQuery("Give me a full readiness assessment"));
    }

    @Test
    @DisplayName("classify: multi-intent gets the UNION of categories")
    void classifyMultiIntent() {
        assertEquals("incidents+deploys",
                Registry.classifyQuery("What was deployed recently and are there any incidents?"));
    }

    @Test
    @DisplayName("classify: no bare 'api' — payment-api doesn't force docs")
    void classifyNoBareApi() {
        assertEquals("docs", Registry.classifyQuery("What does the payment-api spec say?"));
        assertEquals("general", Registry.classifyQuery("Tell me about the service"));
    }

    // ─── Registry ↔ route map consistency ───────────────────────

    @Test
    @DisplayName("PLAN_ROUTE_MAP covers the registry exactly")
    void routeMapMatchesRegistry() {
        Registry.NODE_REGISTRY.forEach((name, spec) ->
                assertEquals(name, Registry.PLAN_ROUTE_MAP.get(name),
                        "registry step '" + name + "' must route to itself"));
        assertEquals("validate", Registry.PLAN_ROUTE_MAP.get("report"));
        assertEquals("validate", Registry.PLAN_ROUTE_MAP.get("done"));
        assertEquals("validate", Registry.PLAN_ROUTE_MAP.get("validate"));
        assertEquals("refuse", Registry.PLAN_ROUTE_MAP.get("refuse"));
        assertEquals(Graph.END, Registry.PLAN_ROUTE_MAP.get("stop"));
        assertEquals(Registry.NODE_REGISTRY.size() + 5, Registry.PLAN_ROUTE_MAP.size());
    }

    @Test
    @DisplayName("registry data fields ↔ REQUIREMENTS agree")
    void registryFieldsMatchRequirements() {
        assertTrue(Registry.FIELD_TO_STEP.containsKey("build_status"));
        assertTrue(Registry.FIELD_TO_STEP.containsKey("deploys"));
        assertTrue(Registry.FIELD_TO_STEP.containsKey("incidents"));
        assertTrue(Registry.FIELD_TO_STEP.containsKey("context"));
        assertEquals(List.of("build_status"), Registry.REQUIREMENTS.get("health"));
        assertEquals(List.of("build_status", "deploys"), Registry.REQUIREMENTS.get("readiness"));
    }

    // ─── Budget guard ───────────────────────────────────────────

    @Test
    @DisplayName("budget trips on steps, resets cleanly")
    void budgetGuard() {
        AgentState state = new AgentState("q");
        int saved = Budget.maxSteps;
        try {
            Budget.maxSteps = 2;
            state.steps = 1;
            assertFalse(Budget.exceeded(state));
            state.steps = 2;
            assertTrue(Budget.exceeded(state));
        } finally {
            Budget.maxSteps = saved;
        }
        assertEquals(10, Budget.maxSteps, "budget must be restored");
    }

    // ─── Validity guard (pure) ──────────────────────────────────

    @Test
    @DisplayName("validate BLOCKS when required data is missing")
    void validateBlocksMissingRequiredData() {
        AgentState state = new AgentState("Is payment-api healthy?");
        Guards.validate(state);
        assertEquals("blocked", state.messages.get(state.messages.size() - 1).getString("status"));
        assertTrue(state.error.contains("REQUIRED DATA MISSING"), state.error);
        assertTrue(state.report.answer().startsWith("Agent stopped before generating a report"));
        assertEquals(ReadinessVerdict.Confidence.LOW, state.report.verdict().confidence());
        assertTrue(state.report.verdict().blockers().get(0).contains("build_status"));
    }

    @Test
    @DisplayName("validate PASSES when required data is present")
    void validatePassesWithRequiredData() {
        AgentState state = new AgentState("Is payment-api healthy?");
        state.buildStatus = "{\"status\": \"healthy\"}";
        Guards.validate(state);
        assertEquals("passed", state.messages.get(state.messages.size() - 1).getString("status"));
        assertEquals("", state.error);
        assertNull(state.report, "a passing guard must not write the report");
    }

    @Test
    @DisplayName("validate BLOCKS on build status 'down' even when present")
    void validateBlocksDownBuild() {
        AgentState state = new AgentState("Is payment-api healthy?");
        state.buildStatus = "{\"status\": \"down\", \"failing_since\": \"2026-06-28T07:30:00Z\"}";
        Guards.validate(state);
        assertTrue(state.error.contains("BUILD FAILING"), state.error);
        assertFalse(state.report.verdict().ready());
    }

    @Test
    @DisplayName("validate: docs query needs context; general query needs nothing")
    void validateCategories() {
        AgentState docs = new AgentState("What does the payment-api spec say?");
        Guards.validate(docs);
        assertTrue(docs.error.contains("'context'"), docs.error);

        AgentState docsOk = new AgentState("What does the payment-api spec say?");
        docsOk.context = "SLA: 99.95%";
        Guards.validate(docsOk);
        assertEquals("", docsOk.error);

        AgentState general = new AgentState("Say hello to DevBuddy");
        Guards.validate(general);
        assertEquals("", general.error);
        assertEquals("passed", general.messages.get(general.messages.size() - 1).getString("status"));
    }

    // ─── Refusal (pure) ─────────────────────────────────────────

    @Test
    @DisplayName("refuse builds the answer FROM the registry")
    void refuseIsRegistryDriven() {
        AgentState state = new AgentState("Deploy auth-service");
        state.record("plan", AgentState.detail("proposal", "deploy", "decision", "refuse"));
        Guards.refuse(state);
        assertTrue(state.error.startsWith("refused: no registered step for 'deploy'"));
        assertTrue(state.report.answer().contains("not an available action"));
        assertTrue(state.report.answer().contains(Registry.refusalList()));
        assertFalse(state.report.answer().contains("deploy,"), "must only list real steps");
    }

    // ─── Edges are pure reads ───────────────────────────────────

    @Test
    @DisplayName("conditional edges only READ state")
    void conditionalEdgesReadState() {
        AgentState state = new AgentState("q");
        state.nextStep = "check_build";
        assertEquals("check_build", Planner.routeFromPlan(state));

        state.report = null;
        assertEquals("generate_report", Guards.routeAfterValidate(state));
        state.report = AgentAnswer.of("blocked");
        assertEquals(Graph.END, Guards.routeAfterValidate(state));
    }

    // ─── Local tool backend (the seam) ──────────────────────────

    @Test
    @DisplayName("TOOL_BACKEND=local serves the same tool payloads as mcp")
    void localBackendServesTools() {
        ToolBackend local = new ToolBackend.LocalBackend();
        String build = local.call("get_build_status", Map.of("service_name", "auth-service"));
        assertTrue(build.contains("\"status\":\"healthy\""), build);
        String deploys = local.call("get_recent_deploys",
                Map.of("service_name", "payment-api", "limit", 3));
        assertTrue(deploys.startsWith("["), deploys);
        assertThrows(ToolFailure.class,
                () -> local.call("no_such_tool", Map.of()));
    }

    @Test
    @DisplayName("failure payloads are detected (status/error shape)")
    void failurePayloadDetection() {
        assertTrue(ToolBackend.looksLikeFailure("{\"status\": \"failed\"}"));
        assertTrue(ToolBackend.looksLikeFailure("{\"error\": \"No data\"}"));
        assertTrue(ToolBackend.looksLikeFailure("not json at all"));
        assertFalse(ToolBackend.looksLikeFailure("{\"status\": \"healthy\"}"));
        assertFalse(ToolBackend.looksLikeFailure("[{\"sha\": \"abc\"}]"));
    }
}