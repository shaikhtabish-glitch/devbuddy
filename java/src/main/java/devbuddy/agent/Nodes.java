package devbuddy.agent;

import com.fasterxml.jackson.databind.JsonNode;
import devbuddy.rag.RagService;
import devbuddy.schemas.Json;
import devbuddy.schemas.JsonSchemas;
import devbuddy.cost.CostTracker;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.metadata.Usage;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.openai.OpenAiChatOptions;

import java.util.List;
import java.util.Map;

/**
 * The graph's nodes — each is one step in the workflow.
 *
 * <p>Node/Python parity: extract_service, retrieve_context, check_build,
 * check_deploys, check_incidents, generate_report (+ the C2 teaching node
 * generate_report_naive). Every node records itself with a per-step cost
 * delta; tool failures land in {@code state.error} + the audit trail, never
 * as a crash.</p>
 */
public class Nodes {

    private final ChatClient chatClient;
    private final String model;
    private final RagService rag;
    private final ToolBackend tools;

    public Nodes(ChatClient chatClient, String model, RagService rag, ToolBackend tools) {
        this.chatClient = chatClient;
        this.model = model;
        this.rag = rag;
        this.tools = tools;
    }

    // ─── LLM plumbing ───────────────────────────────────────────

    /** One completion: its text + what it cost (per-call, not shared state). */
    private record Completion(String text, double cost) {
    }

    /** Plain text completion. */
    private Completion complete(String system, String user) {
        return complete(system, user, null);
    }

    private Completion complete(String system, String user, OpenAiChatOptions extra) {
        var builder = chatClient.prompt().system(system).user(user);
        if (extra != null) {
            builder = builder.options(extra);
        }
        ChatResponse response = builder.call().chatResponse();
        return new Completion(response.getResult().getOutput().getText(), usageCost(response));
    }
    private double usageCost(ChatResponse response) {
        Usage usage = response.getMetadata() == null ? null : response.getMetadata().getUsage();
        long prompt = usage != null && usage.getPromptTokens() != null ? usage.getPromptTokens() : 0L;
        long completion = usage != null && usage.getCompletionTokens() != null ? usage.getCompletionTokens() : 0L;
        return CostTracker.calculateCost(model, prompt, completion);
    }

    private OpenAiChatOptions agentAnswerOptions() {
        return OpenAiChatOptions.builder()
                .model(model)
                .temperature(0.0)
                .responseFormat(JsonSchemas.responseFormat("agent_answer", JsonSchemas.AGENT_ANSWER))
                .build();
    }

    // ─── Node: extract_service ──────────────────────────────────

    public AgentState extractService(AgentState state) {
        if (!state.serviceName.isEmpty()) {
            state.record("extract_service", AgentState.detail(
                    "service", state.serviceName, "cached", true));
            return state;
        }
        String name = "";
        try {
            Completion first = complete(
                    "Extract the service name from the user's query. " +
                            "Respond with EXACTLY ONE WORD: the service name. " +
                            "Known services: auth-service, payment-api, inventory-service. " +
                            "If no service is mentioned, respond with 'payment-api' as default.",
                    state.query);
            state.cost += first.cost();
            name = first.text().trim().toLowerCase();
            if (name.isEmpty()) {
                // empty completion (provider quirk at temp=0) — retry once
                Completion second = complete("", state.query + "\n\nService name:");
                state.cost += second.cost();
                name = second.text().trim().toLowerCase();
            }
        } catch (Exception ignored) {
            // LLM failure → default below; the run continues
        }
        if (name.isEmpty()) {
            name = "payment-api";
        }
        state.serviceName = name;
        state.steps++;
        state.record("extract_service", AgentState.detail("service", name));
        return state;
    }

    // ─── Node: retrieve_context ─────────────────────────────────

    public AgentState retrieveContext(AgentState state) {
        try {
            List<String> chunks = rag.retrieve(state.query, 3);
            state.context = chunks.isEmpty()
                    ? "(no relevant documents found)"
                    : String.join("\n\n---\n\n", chunks);
            state.record("retrieve_context", AgentState.detail("chunks", chunks.size()));
        } catch (Exception e) {
            // Retrieval failed → context stays empty AND the failure is visible.
            state.context = "";
            toolFailure(state, "retrieve_context", e.getMessage());
        }
        state.steps++;
        return state;
    }

    // ─── Nodes: tool-backed checks ──────────────────────────────

    public AgentState checkBuild(AgentState state) {
        try {
            String raw = tools.call("get_build_status",
                    Map.of("service_name", defaultService(state)));
            JsonNode data = Json.MAPPER.readTree(raw);
            if (!data.has("status")) {
                throw new ToolFailure("no status field: " + raw);
            }
            state.buildStatus = raw;
            state.record("check_build", AgentState.detail("status", data.get("status").asText()));
        } catch (Exception e) {
            toolFailure(state, "check_build", e.getMessage());
        }
        state.steps++;
        return state;
    }

    public AgentState checkDeploys(AgentState state) {
        try {
            String raw = tools.call("get_recent_deploys",
                    Map.of("service_name", defaultService(state), "limit", 3));
            JsonNode data = Json.MAPPER.readTree(raw);
            if (!data.isArray()) {
                throw new ToolFailure("expected an array: " + raw);
            }
            state.deploys = raw;
            state.record("check_deploys", AgentState.detail("count", data.size()));
        } catch (Exception e) {
            toolFailure(state, "check_deploys", e.getMessage());
        }
        state.steps++;
        return state;
    }

    public AgentState checkIncidents(AgentState state) {
        try {
            String raw = tools.call("get_active_incidents",
                    Map.of("service_name", defaultService(state)));
            JsonNode data = Json.MAPPER.readTree(raw);
            if (!data.isArray()) {
                throw new ToolFailure("expected an array: " + raw);
            }
            state.incidents = raw;
            state.record("check_incidents", AgentState.detail("count", data.size()));
        } catch (Exception e) {
            toolFailure(state, "check_incidents", e.getMessage());
        }
        state.steps++;
        return state;
    }

    private String defaultService(AgentState state) {
        return state.serviceName.isEmpty() ? "payment-api" : state.serviceName;
    }

    // ─── Report generation (structured, contract-enforced) ──────

    static final String REPORT_RULES =
            "You are a site reliability engineer. Answer the user's query using ONLY " +
            "the data provided below. Rules:\n" +
            "- If a section says NOT CHECKED, say so plainly — never invent data for it.\n" +
            "- If build status is 'degraded' or 'down', verdict.ready must be false " +
            "and blockers must say why.\n" +
            "- Set a verdict (ready/blockers/next steps) for readiness or health queries; " +
            "leave verdict null for docs or general questions.\n" +
            "- verdict.confidence must be 'low' unless evidence supports it.\n" +
            "- Every claim must cite its source in evidence: 'rag' for documentation, " +
            "'tool' for build/deploy/incident data, 'user' for the query itself.\n" +
            "- ready=true with blockers, or ready=false with no blockers, will be " +
            "REJECTED by the contract validator — be consistent.";

    static final String NAIVE_SYSTEM =
            "You are a site reliability engineer. Generate a complete release " +
            "readiness report based on the following data. Be specific and " +
            "decisive: state the build health, the deployment state, and whether " +
            "the service is ready to ship. Return an AgentAnswer.";

    public AgentState generateReport(AgentState state) {
        String sections = String.join("\n\n",
                "Query: " + state.query,
                dataSection("Relevant documentation", state.context),
                dataSection("Build status", state.buildStatus),
                dataSection("Recent deployments", state.deploys),
                dataSection("Active incidents", state.incidents));
        invokeStructured(REPORT_RULES, "Query + data:\n\n" + sections, state, "generate_report");
        state.steps++;
        return state;
    }

    /** C2 teaching node — DELIBERATELY UNDEFENDED (demo-04 only):
     *  renders missing state as '{}' and gives the model NO ground rules. */
    public AgentState generateReportNaive(AgentState state) {
        String sections = String.join("\n\n",
                "Query: " + state.query,
                naiveDataSection("Relevant documentation", state.context),
                naiveDataSection("Build status", state.buildStatus),
                naiveDataSection("Recent deployments", state.deploys),
                naiveDataSection("Active incidents", state.incidents));
        invokeStructured(NAIVE_SYSTEM, "Query + data:\n\n" + sections, state, "generate_report_naive");
        state.steps++;
        return state;
    }

    /** None-ish ("") means NOT CHECKED — and it says so, in caps. */
    private static String dataSection(String label, String value) {
        return (value == null || value.isEmpty())
                ? label + ": NOT CHECKED (step was skipped or failed)"
                : label + ":\n" + value;
    }

    /** The VULNERABLE rendering: missing state becomes '{}'. */
    private static String naiveDataSection(String label, String value) {
        return (value == null || value.isEmpty())
                ? label + ": {}"
                : label + ":\n" + value;
    }

    /**
     * Structured call through {@code response_format=json_schema} — the API
     * enforces the SHAPE, the record constructor enforces the cross-field
     * contract. One perturbed retry: identical requests at temp=0 can replay
     * a stuck/empty completion (the provider quirk Python guards with
     * {@code _final_answer}'s nudge). response_format is a plain JSON body
     * (not function-calling), the request class that never stalled on Node.
     */
    private void invokeStructured(String system, String sections, AgentState state, String step) {
        String lastError = null;
        for (int attempt = 1; attempt <= 2; attempt++) {
            String human = attempt == 1 ? sections
                    : sections + "\n\n(Attempt " + attempt + " — respond now, in an AgentAnswer.)";
            try {
                ChatResponse response = chatClient.prompt()
                        .system(system)
                        .user(human)
                        .options(agentAnswerOptions())
                        .call()
                        .chatResponse();
                state.cost += usageCost(response);
                String raw = Json.stripMarkdownFences(
                        response.getResult().getOutput().getText());
                AgentAnswer answer = Json.parse(raw, AgentAnswer.class); // contract enforced
                state.report = answer;
                state.record(step, AgentState.detail(
                        "ready", answer.verdict() == null ? null : answer.verdict().ready(),
                        "evidence", answer.evidence().size()));
                return;
            } catch (Exception e) {
                lastError = String.valueOf(e.getMessage() == null ? e : e.getMessage());
            }
        }
        // Contract violation at the boundary: surfaced, never hidden.
        state.error = step + ": " + lastError;
        state.report = AgentAnswer.of(
                "(report generation failed — the model's output did not satisfy " +
                        "the AgentAnswer contract. See error.)");
        state.record(step, AgentState.detail("status", "failed", "error", lastError));
    }

    // ─── Shared failure path ────────────────────────────────────

    private void toolFailure(AgentState state, String step, String message) {
        state.error = step + ": " + message;
        state.record(step, AgentState.detail("status", "failed", "error", message));
    }

    /** Registry step name → node function (how the dynamic graph wires them). */
    public Graph.Node forStep(String registryStep) {
        return switch (registryStep) {
            case "retrieve" -> this::retrieveContext;
            case "check_build" -> this::checkBuild;
            case "check_deploys" -> this::checkDeploys;
            case "check_incidents" -> this::checkIncidents;
            default -> throw new IllegalArgumentException(
                    "No node function for registry step '" + registryStep + "'");
        };
    }
}