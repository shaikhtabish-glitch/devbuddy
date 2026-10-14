package devbuddy.agent;

import com.fasterxml.jackson.databind.JsonNode;
import devbuddy.schemas.Json;
import devbuddy.schemas.ReadinessVerdict;

import java.util.ArrayList;
import java.util.List;

/**
 * The guards that don't need an LLM — written in code, typed answers out.
 *
 * <ul>
 *   <li>{@link #validate} — Guard 3 (business/validity): required state
 *       present &amp; acceptable BEFORE generate_report; on failure it
 *       writes the blocked report itself.</li>
 *   <li>{@link #refuse} — registry-driven refusal; the message is
 *       CONSTRUCTED from the registry, never model prose.</li>
 * </ul>
 */
public final class Guards {

    private Guards() {
    }

    /**
     * Validity guard: is the state acceptable for THIS query's report?
     * On failure it writes the blocked report itself — typed, zero LLM.
     */
    public static AgentState validate(AgentState state) {
        String category = Registry.classifyQuery(state.query); // e.g. "incidents+deploys"
        List<String> reasons = new ArrayList<>();
        List<String> nextSteps = new ArrayList<>();

        for (String field : Registry.requiredMissing(state)) {
            String step = Registry.FIELD_TO_STEP.getOrDefault(field, field);
            reasons.add("REQUIRED DATA MISSING: '" + field + "' was never collected "
                    + "(step '" + step + "' skipped or failed)");
            nextSteps.add("Run " + step + " before answering this query");
        }

        if (state.filled("build_status")) {
            try {
                JsonNode build = Json.MAPPER.readTree(state.buildStatus);
                String status = build.path("status").asText("");
                if (status.equals("down")) {
                    String since = build.has("failing_since")
                            ? " since " + build.get("failing_since").asText() : "";
                    reasons.add("BUILD FAILING: status 'down'" + since);
                    nextSteps.add("Fix the failing build before release");
                }
            } catch (Exception e) {
                reasons.add("BUILD STATUS UNPARSEABLE: contract violation in tool output");
                nextSteps.add("Inspect the get_build_status tool output");
            }
        }

        if (!reasons.isEmpty()) {
            state.error = "guard (" + category + "): " + String.join("; ", reasons);
            state.report = blockedAnswer(reasons, nextSteps);
            state.record("validate", AgentState.detail("status", "blocked", "category", category));
        } else {
            state.record("validate", AgentState.detail("status", "passed", "category", category));
        }
        return state;
    }

    /**
     * Conditional edge after validate: blocked = the guard already wrote the
     * report → stop. Pass = no report yet → let the model generate one.
     */
    public static String routeAfterValidate(AgentState state) {
        return state.report != null ? Graph.END : "generate_report";
    }

    /** Registry-driven refusal. */
    public static AgentState refuse(AgentState state) {
        String proposal = "unknown action";
        for (int i = state.messages.size() - 1; i >= 0; i--) {
            AuditRecord m = state.messages.get(i);
            if ("plan".equals(m.step()) && m.get("proposal") != null) {
                proposal = m.getString("proposal");
                break;
            }
        }
        String available = Registry.refusalList();
        state.error = "refused: no registered step for '" + proposal + "'";
        state.report = new AgentAnswer(
                "I can't do that — '" + proposal + "' is not an available action. "
                        + "DevBuddy can: " + available + ".",
                new ReadinessVerdict(false, ReadinessVerdict.Confidence.LOW,
                        List.of("Requested action '" + proposal + "' has no registered tool"),
                        List.of("Ask for one of: " + available)),
                List.of());
        state.record("refuse", AgentState.detail("action", proposal));
        return state;
    }

    /** The guard's output: a typed, deterministic answer — not prose. */
    public static AgentAnswer blockedAnswer(List<String> reasons, List<String> nextSteps) {
        return new AgentAnswer(
                "Agent stopped before generating a report: " + String.join("; ", reasons),
                new ReadinessVerdict(false, ReadinessVerdict.Confidence.LOW,
                        reasons, nextSteps),
                List.of());
    }
}