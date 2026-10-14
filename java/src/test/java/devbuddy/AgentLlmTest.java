package devbuddy;

import devbuddy.agent.*;
import devbuddy.config.AppConfig;
import devbuddy.rag.RagService;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Week 6 — agent flows that need the LLM and (for integration) Qdrant.
 *
 * <p>Mirrors the e2e portions of {@code tests/test_agent.py} /
 * {@code tests/test_agent.js}. Uses {@code TOOL_BACKEND=local} so no MCP
 * server is needed — the seam serves identical payloads. Integration tests
 * degrade cleanly: they're skipped (JUnit assumption) when Qdrant (:6334)
 * is down or no API key is configured.</p>
 *
 * <p>Run: {@code mvn test -Dtest=AgentLlmTest}</p>
 */
class AgentLlmTest {

    private static AnnotationConfigApplicationContext ctx;
    private static Agents agents;
    private static boolean qdrantUp;
    private static boolean llmConfigured;

    @BeforeAll
    static void setUp() {
        System.setProperty("TOOL_BACKEND", "local");
        qdrantUp = portOpen(6334);
        llmConfigured = !System.getenv().getOrDefault("OPENROUTER_API_KEY", "").isBlank()
                || new java.io.File("src/main/resources/application.properties").exists();
        if (llmConfigured) {
            ctx = new AnnotationConfigApplicationContext(AppConfig.class);
            agents = ctx.getBean(Agents.class);
        }
    }

    @AfterAll
    static void tearDown() {
        if (ctx != null) {
            ctx.close();
        }
        System.clearProperty("TOOL_BACKEND");
    }

    private static boolean portOpen(int port) {
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress("127.0.0.1", port), 500);
            return true;
        } catch (IOException e) {
            return false;
        }
    }

    private static void requireLlm() {
        Assumptions.assumeTrue(llmConfigured, "needs OPENROUTER_API_KEY / application.properties");
    }

    private static void requireQdrant() {
        requireLlm();
        Assumptions.assumeTrue(qdrantUp, "needs Qdrant on :6334");
        // the collection must be indexed for retrieval to return context
        RagService rag = ctx.getBean(RagService.class);
        try {
            rag.indexDocuments(null, 512, 64);
        } catch (Exception e) {
            Assumptions.abort("Qdrant index failed: " + e.getMessage());
        }
    }

    // ─── Refusal e2e — no tools, no Qdrant, just the LLM ────────

    @Test
    @DisplayName("refusal e2e: 'Deploy ...' refused from the registry, pre-tools")
    void refusalEndToEnd() {
        requireLlm();
        AgentState result = agents.runDynamicAgent("Deploy auth-service to production");
        assertTrue(result.error.startsWith("refused: no registered step"), result.error);
        assertNotNull(result.report);
        assertTrue(result.report.answer().contains("not an available action"),
                result.report.answer());
        assertTrue(result.report.answer().contains(Registry.refusalList()));
        assertTrue(result.path().contains("refuse"), result.path().toString());
        assertFalse(result.path().contains("check_build"), "no tool should run before refusal");
    }

    // ─── Integration flows (Qdrant + LLM, local backend) ────────

    @Test
    @DisplayName("fixed chain runs 4 nodes and produces a structured report")
    void fixedChainRuns() {
        requireQdrant();
        AgentState result = agents.runFixedChain("Is the payment-api ready for release?");
        assertEquals(List.of("extract_service", "retrieve_context", "check_build",
                "generate_report"), result.path());
        assertTrue(result.steps >= 4, "steps=" + result.steps);
        assertNotNull(result.report, "report must be generated: " + result.error);
        assertFalse(result.report.answer().isEmpty());
        assertFalse(result.messages.isEmpty());
        assertTrue(result.cost > 0);
    }

    @Test
    @DisplayName("guarded chain PASSES when build data is present (auth-service)")
    void guardedChainPasses() {
        requireQdrant();
        AgentState result = agents.runGuardedChain("Is auth-service healthy?", true);
        assertTrue(result.path().contains("validate"), result.path().toString());
        String validateStatus = result.messages.stream()
                .filter(m -> "validate".equals(m.step()))
                .findFirst().orElseThrow().getString("status");
        assertEquals("passed", validateStatus, "guard must pass: " + result.error);
        assertEquals("", result.error);
        assertNotNull(result.report);
        assertTrue(result.path().contains("generate_report"), result.path().toString());
    }

    @Test
    @DisplayName("guarded chain BLOCKS when check_build is removed — no report call")
    void guardedChainBlocks() {
        requireQdrant();
        AgentState result = agents.runGuardedChain("Is auth-service healthy?", false);
        assertFalse(result.path().contains("check_build"), "node must be absent from the graph");
        assertFalse(result.path().contains("generate_report"), "guard must stop the report");
        assertEquals("", result.buildStatus, "build must never be collected");
        assertTrue(result.error.startsWith("guard ("), result.error);
        assertTrue(result.error.contains("REQUIRED DATA MISSING"), result.error);
        assertNotNull(result.report, "typed blocked answer must exist");
        assertTrue(result.report.answer().startsWith("Agent stopped before generating"));
        assertTrue(result.cost < 0.001, "blocked run must be nearly free: $" + result.cost);
    }

    @Test
    @DisplayName("missing-step graph runs WITHOUT check_build — C2, no guard")
    void missingStepGraphRuns() {
        requireQdrant();
        AgentState result = agents.runMissingStepAgent("Is payment-api ready for release?");
        assertEquals(List.of("extract_service", "retrieve_context", "check_deploys",
                "generate_report_naive"), result.path());
        assertEquals("", result.buildStatus, "the removed node must leave empty state");
        assertEquals("", result.error, "the naive flow must not report tool errors");
        assertNotNull(result.report, "naive report generation failed: " + result.error);
        assertFalse(result.report.answer().contains("report generation failed"),
                "report must come from the model, not the failure fallback");
    }
}