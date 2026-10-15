package devbuddy.scripts.week06;

import com.fasterxml.jackson.databind.ObjectMapper;
import devbuddy.agent.AgentState;
import devbuddy.agent.Agents;

import java.util.Map;

/**
 * Week 6 — shared helpers for the agent demos (Java).
 *
 * <p>Mirrors {@code week05/DemoSupport}'s header/border style; the demos are
 * otherwise self-contained so learners can read one file top to bottom.</p>
 */
public final class DemoSupport {

    public static final String BORDER = "=".repeat(65);

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private DemoSupport() {
    }

    public static void header(String title) {
        System.out.println(BORDER);
        System.out.println("  " + title);
        System.out.println(BORDER);
    }

    /** Compact single-line JSON for audit detail maps (JSON.stringify parity). */
    public static String compact(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            return String.valueOf(value);
        }
    }

    /** The recorded path: extract_service → plan → … */
    public static String path(AgentState state) {
        return String.join(" → ", state.path());
    }

    /** Cost line, matching the other languages' output. */
    public static String costLine(AgentState state) {
        return String.format("%.6f", state.cost);
    }

    /** Report + guard error + totals — printed by every demo. */
    public static void showReport(Agents agents, AgentState state) {
        System.out.println(Agents.formatReport(state.report));
    }

    /**
     * Index shared/data into Qdrant for THIS process — RagService.requireIndexed()
     * checks an in-memory flag, so a fresh demo boot must index before retrieval
     * works (the same explicit step week-03 demos take). Degrades visibly: if
     * Qdrant is down, the retrieve node records a failure instead of crashing.
     */
    public static void primeIndex(org.springframework.context.annotation.AnnotationConfigApplicationContext ctx) {
        try {
            devbuddy.rag.RagService rag = ctx.getBean(devbuddy.rag.RagService.class);
            int chunks = rag.indexDocuments(null, 512, 64);
            System.out.println("  📚 indexed " + chunks + " chunks for this run (Qdrant :6334)");
            System.out.println();
        } catch (Exception e) {
            System.out.println("  ⚠️  index unavailable: " + e.getMessage());
            System.out.println("      retrieval will record a visible failure in the audit trail");
            System.out.println();
        }
    }
}