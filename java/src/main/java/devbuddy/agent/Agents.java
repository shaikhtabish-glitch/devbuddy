package devbuddy.agent;

import devbuddy.rag.RagService;
import org.springframework.ai.chat.client.ChatClient;

/**
 * The agent facade — builds the four graphs and runs them.
 *
 * <ul>
 *   <li>{@link #buildFixedChain()} — C1: fixed 4-step chain, hardcoded edges.</li>
 *   <li>{@link #buildDynamicAgent()} — plan → registry → act, in a loop.</li>
 *   <li>{@link #buildGuardedChain(boolean)} — C3: fixed chain + validity guard
 *       ({@code includeBuild=false} reproduces C2's missing-step graph WITH
 *       the guard attached).</li>
 *   <li>{@link #buildMissingStepAgent()} — C2: check_build REMOVED, no guard,
 *       naive report node.</li>
 * </ul>
 *
 * <p>Same teaching architecture as Python's {@code agent.py} and Node's
 * {@code agent.js}; the graph runtime itself is the hand-rolled state machine
 * described in {@link Graph}.</p>
 */
public class Agents {

    private final Nodes nodes;
    private final Planner planner;

    public Agents(ChatClient chatClient, String model, RagService rag) {
        this(chatClient, model, rag, ToolBackend.fromEnv());
    }

    public Agents(ChatClient chatClient, String model, RagService rag, ToolBackend tools) {
        this.nodes = new Nodes(chatClient, model, rag, tools);
        this.planner = new Planner(chatClient, model);
    }

    public Nodes nodes() {
        return nodes;
    }

    // ─── Builders ───────────────────────────────────────────────

    /** C1: fixed chain — same edges both queries: extract → retrieve → check_build → generate_report. */
    public Graph buildFixedChain() {
        return Graph.from("extract_service")
                .node("extract_service", nodes::extractService)
                .node("retrieve", nodes::retrieveContext)
                .node("check_build", nodes::checkBuild)
                .node("generate_report", nodes::generateReport)
                .link("extract_service", "retrieve")
                .link("retrieve", "check_build")
                .link("check_build", "generate_report")
                .end("generate_report")
                .build();
    }

    /**
     * C3: fixed chain + validity guard before the report.
     * {@code includeBuild=false} = the missing-step graph WITH the guard.
     */
    public Graph buildGuardedChain(boolean includeBuild) {
        Graph.Builder b = Graph.from("extract_service")
                .node("extract_service", nodes::extractService)
                .node("retrieve", nodes::retrieveContext)
                .node("check_deploys", nodes::checkDeploys)
                .node("validate", Guards::validate)
                .node("generate_report", nodes::generateReport)
                .link("extract_service", "retrieve")
                .link("check_deploys", "validate")
                .branch("validate", Guards::routeAfterValidate)
                .end("generate_report");

        if (includeBuild) {
            b.node("check_build", nodes::checkBuild);
            b.link("retrieve", "check_build").link("check_build", "check_deploys");
        } else {
            // check_build NOT registered at all — the state field stays empty
            // by design (a registered-but-unwired node would be unreachable).
            b.link("retrieve", "check_deploys");
        }
        return b.build();
    }

    /**
     * C2: check_build REMOVED and NO guard — the naive report node fills the
     * gap the missing node left behind.
     */
    public Graph buildMissingStepAgent() {
        return Graph.from("extract_service")
                .node("extract_service", nodes::extractService)
                .node("retrieve", nodes::retrieveContext)
                .node("check_deploys", nodes::checkDeploys)
                .node("generate_report_naive", nodes::generateReportNaive)
                .link("extract_service", "retrieve")
                .link("retrieve", "check_deploys")
                .link("check_deploys", "generate_report_naive")
                .end("generate_report_naive")
                .build();
    }

    /**
     * Dynamic agent: plan → registry → act, in a loop. One planner node,
     * ONE conditional edge reading state, validity guard before the report.
     */
    public Graph buildDynamicAgent() {
        Graph.Builder b = Graph.from("extract_service")
                .node("extract_service", nodes::extractService)
                .node("plan", planner::plan)
                .node("validate", Guards::validate)
                .node("refuse", Guards::refuse)
                .node("generate_report", nodes::generateReport)
                .link("extract_service", "plan")
                // conditional edge: planner's decision → registry route map
                .branch("plan", state ->
                        Registry.PLAN_ROUTE_MAP.getOrDefault(
                                Planner.routeFromPlan(state), Graph.END))
                .branch("validate", Guards::routeAfterValidate);

        // Every registry step loops back to the planner.
        for (String step : Registry.NODE_REGISTRY.keySet()) {
            b.node(step, nodes.forStep(step)).link(step, "plan");
        }
        b.end("refuse").end("generate_report");
        return b.build();
    }

    // ─── Runners ────────────────────────────────────────────────

    public AgentState runFixedChain(String query) {
        return buildFixedChain().run(new AgentState(query));
    }

    public AgentState runDynamicAgent(String query) {
        return buildDynamicAgent().run(new AgentState(query));
    }

    public AgentState runGuardedChain(String query, boolean includeBuild) {
        return buildGuardedChain(includeBuild).run(new AgentState(query));
    }

    public AgentState runMissingStepAgent(String query) {
        return buildMissingStepAgent().run(new AgentState(query));
    }

    // ─── Report rendering — shared by every demo ────────────────

    public static String formatReport(AgentAnswer report) {
        if (report == null) {
            return "(no report generated)";
        }
        StringBuilder sb = new StringBuilder(report.answer());
        var v = report.verdict();
        if (v != null) {
            sb.append("\n\n  ready      : ").append(v.ready())
                    .append("  (confidence: ").append(v.confidence().value()).append(")");
            for (String b : v.blockers()) {
                sb.append("\n  blocker    : ").append(b);
            }
            for (String n : v.recommendedNextSteps()) {
                sb.append("\n  next step  : ").append(n);
            }
        }
        if (!report.evidence().isEmpty()) {
            sb.append('\n');
            for (var e : report.evidence()) {
                String score = e.relevanceScore() == null ? "" : " (" + e.relevanceScore() + ")";
                String content = e.content().substring(0, Math.min(100, e.content().length()));
                sb.append("\n  evidence[").append(e.source().value()).append(']')
                        .append(score).append(": ").append(content);
            }
        }
        return sb.toString();
    }
}