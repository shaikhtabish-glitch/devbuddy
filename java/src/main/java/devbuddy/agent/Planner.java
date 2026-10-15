package devbuddy.agent;

import devbuddy.cost.CostTracker;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.model.ChatResponse;

import java.util.Map;
import java.util.Set;

/**
 * Guard 2 — plan: the model PROPOSES, the registry disposes (structural).
 *
 * <p>Imperative actions refused pre-LLM, unknown capabilities refused via
 * registry, repeats corrected once then handed to the guard's fallback. The
 * accepted decision lands in {@code state.nextStep} — the conditional edge
 * ({@link #routeFromPlan}) only READS state.</p>
 *
 * <p>Mirror of Python's {@code plan()} / Node's {@code plan()}.</p>
 */
public class Planner {

    private final ChatClient chatClient;
    private final String model;

    public Planner(ChatClient chatClient, String model) {
        this.chatClient = chatClient;
        this.model = model;
    }

    /** LLM proposes the next step — one word from the registry-generated catalog. */
    private String router(AgentState state, String correction) {
        String system =
                "You are a workflow router. Based on the user's query and what data " +
                "has already been collected, propose the NEXT step. Respond with " +
                "EXACTLY ONE WORD from this list:\n\n" +
                Registry.routerCatalog() + "\n\n" +
                "Rules:\n" +
                "- Only run steps the query explicitly asks for. Do NOT cascade: " +
                "'healthy?' does not mean 'also check incidents'.\n" +
                "- NEVER propose a step whose data is already YES below.\n" +
                "- Docs/API/spec/SLA questions → retrieve only. Health/status → check_build " +
                "only. Deployments → check_deploys only. Incidents → check_incidents only.\n" +
                "- Propose 'report' as soon as everything the query needs is YES.\n" +
                "- If instead the query asks you to PERFORM an operational action " +
                "(deploy, rollback, restart, scale, delete), respond with that single " +
                "action word — it will be checked against the registry.\n" +
                (correction == null ? "" : "CORRECTION: " + correction + "\n");

        String user =
                "QUERY: " + state.query + "\n\n" +
                "CURRENT STATE:\n" +
                "- Steps completed: " + state.steps + "\n" +
                "- Context retrieved: " + (state.filled("context") ? "YES" : "NO") + "\n" +
                "- Build status checked: " + (state.filled("build_status") ? "YES" : "NO") + "\n" +
                "- Deploys checked: " + (state.filled("deploys") ? "YES" : "NO") + "\n" +
                "- Incidents checked: " + (state.filled("incidents") ? "YES" : "NO") + "\n\n" +
                "NEVER return a step that already has data (YES above). " +
                "If all needed data is YES, return 'report'.\n\n" +
                "Next step:";

        try {
            ChatResponse response = chatClient.prompt()
                    .system(system)
                    .user(user)
                    .call()
                    .chatResponse();
            state.cost += CostTracker.calculateCost(model,
                    promptTokens(response), completionTokens(response));
            String decision = response.getResult().getOutput().getText().trim().toLowerCase();
            if (!decision.isEmpty()) {
                return decision;
            }
        } catch (Exception ignored) {
            // fall through to the empty-proposal retry below
        }

        // empty completion — retry once before trusting an empty proposal
        try {
            ChatResponse response = chatClient.prompt()
                    .user("QUERY: " + state.query + "\n\nAvailable steps:\n"
                            + Registry.routerCatalog() + "\n\nNext step (one word):")
                    .call()
                    .chatResponse();
            state.cost += CostTracker.calculateCost(model,
                    promptTokens(response), completionTokens(response));
            return response.getResult().getOutput().getText().trim().toLowerCase();
        } catch (Exception e) {
            return "";
        }
    }

    private static long promptTokens(ChatResponse response) {
        var u = response.getMetadata() == null ? null : response.getMetadata().getUsage();
        return u != null && u.getPromptTokens() != null ? u.getPromptTokens() : 0L;
    }

    private static long completionTokens(ChatResponse response) {
        var u = response.getMetadata() == null ? null : response.getMetadata().getUsage();
        return u != null && u.getCompletionTokens() != null ? u.getCompletionTokens() : 0L;
    }

    /**
     * Planner node — propose next step, validate it against the registry.
     */
    public AgentState plan(AgentState state) {
        if (Budget.exceeded(state)) {
            if (state.report == null) {
                state.report = Guards.blockedAnswer(
                        java.util.List.of("AGENT BUDGET EXCEEDED: step/cost ceiling reached "
                                + "before a report was produced"),
                        java.util.List.of("Raise the budget, or narrow the query"));
            }
            state.nextStep = "stop"; // → PLAN_ROUTE_MAP: stop → END
            state.record("plan", AgentState.detail(
                    "decision", "stop", "reason", "budget exceeded"));
            return state;
        }

        // Deterministic refusal — imperative action, before any LLM call.
        var imperative = Registry.IMPERATIVE_ACTIONS.matcher(state.query.toLowerCase());
        if (imperative.find()) {
            state.nextStep = "refuse";
            state.record("plan", AgentState.detail(
                    "proposal", imperative.group(1).replaceAll("\\s+", "_"),
                    "decision", "refuse",
                    "reason", "imperative action — registry check before any LLM call"));
            return state;
        }

        // Structural scope: which steps are worth proposing for THIS query?
        Set<String> allowed = Registry.allowedSteps(state.query);

        String proposal = router(state, null);
        Set<String> known = Registry.knownDecisions();

        if (!known.contains(proposal)) {
            // The model asked for a capability that does not exist → refuse.
            state.nextStep = "refuse";
            state.record("plan", AgentState.detail(
                    "proposal", proposal, "decision", "refuse", "reason", "not in registry"));
            return state;
        }

        if (!Registry.stepOk(proposal, state, allowed)) {
            // Already collected, out of scope, or already failed → re-ask ONCE;
            // if the model can't course-correct, the GUARD decides.
            String original = proposal;
            String needed = allowed.stream()
                    .filter(s -> Registry.stepOk(s, state, allowed))
                    .reduce((a, b) -> a + ", " + b).orElse("none");
            String retry = router(state,
                    "'" + proposal + "' is not appropriate right now — it is either already " +
                            "collected, already failed, or not needed for this query type. " +
                            "Needed steps: " + needed + ". Propose one of those, or 'report'.");
            if (known.contains(retry) && Registry.stepOk(retry, state, allowed)) {
                state.nextStep = retry;
                state.record("plan", AgentState.detail(
                        "proposal", original, "decision", "corrected", "corrected_to", retry));
                return state;
            }
            String fallback = Registry.requiredMissing(state).isEmpty() ? "report" : "validate";
            state.nextStep = fallback;
            state.record("plan", AgentState.detail(
                    "proposal", original, "decision", "fallback", "corrected_to", fallback));
            return state;
        }

        state.nextStep = proposal;
        state.record("plan", AgentState.detail("proposal", proposal, "decision", "accept"));
        return state;
    }

    /** The edge is a pure read — plan() already made the decision. */
    public static String routeFromPlan(AgentState state) {
        return state.nextStep;
    }
}