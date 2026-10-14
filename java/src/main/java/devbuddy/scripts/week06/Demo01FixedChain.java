package devbuddy.scripts.week06;

import devbuddy.agent.AgentState;
import devbuddy.agent.Agents;
import devbuddy.agent.AuditRecord;
import devbuddy.agent.Graph;
import devbuddy.config.AppConfig;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

/**
 * Demo 1 (C1): Fixed Chain — a state machine, not a for-loop.
 *
 * <p>{@code buildFixedChain()} compiles nodes + hardcoded edges into the
 * graph runtime. We RUN it with a transition listener: after every hop you
 * see which state fields the node filled — and which are still empty (that
 * emptiness is the fuel for C2, demo-04).</p>
 *
 * <p>Requires: MCP server ({@code mvn -q compile exec:java
 * -Dexec.mainClass=devbuddy.mcp.DevBuddyMcpServer}, :8002) + Qdrant (:6334).</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week06.Demo01FixedChain}</p>
 */
public class Demo01FixedChain {

    private static final String[] DATA_FIELDS = {
            "service_name", "context", "build_status", "deploys", "incidents", "report"
    };

    public static void main(String[] args) {
        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            Agents agents = ctx.getBean(Agents.class);

            DemoSupport.header("Demo 1 (C1): Fixed Chain — the graph drives the transitions");
            System.out.println();
            System.out.println("  Nodes are functions. Edges are hardcoded. The RUNTIME walks");
            System.out.println("  them — nothing below is a hand-written for-loop.");
            System.out.println();

            DemoSupport.primeIndex(ctx);

            traceFixedChain(agents, "Is the payment-api ready for v2.1?");
            traceFixedChain(agents, "Is the auth-service ready for release?");

            System.out.println(DemoSupport.BORDER);
            System.out.println("  Fixed chain: same edges, same order, both queries — 4 nodes.");
            System.out.println("  🔀  extract → retrieve → check_build → generate_report → END");
            System.out.println("  Predictable and auditable, but it CANNOT skip a step or add");
            System.out.println("  one (no deploys/incidents nodes here). See demo-02 for a graph");
            System.out.println("  whose edges are chosen at runtime.");
            System.out.println(DemoSupport.BORDER);
            System.out.println();
        }
        System.exit(0);
    }

    private static void traceFixedChain(Agents agents, String query) {
        AgentState state = new AgentState(query);
        System.out.println("  📥  QUERY: \"" + query + "\"");
        System.out.println("  " + "-".repeat(59));

        final int[] seen = {0};
        Graph graph = agents.buildFixedChain();
        graph.run(state, (node, s) -> {
            var newEvents = s.messages.subList(seen[0], s.messages.size());
            seen[0] = s.messages.size();

            StringBuilder filled = new StringBuilder();
            StringBuilder pending = new StringBuilder();
            for (String f : DATA_FIELDS) {
                if (s.filled(f)) {
                    filled.append(f).append(", ");
                } else {
                    pending.append(f).append(", ");
                }
            }

            System.out.println("  ▶ " + node);
            for (AuditRecord audit : newEvents) {
                var detail = new java.util.LinkedHashMap<>(audit.detail());
                detail.remove("cost");
                System.out.println("      audit      : " + DemoSupport.compact(detail)
                        + "  · $" + String.format("%.6f", audit.cost()));
            }
            System.out.println("      filled     : " + trim(filled.toString()));
            System.out.println("      still empty: " + trim(pending.toString())
                    + (pending.length() > 0
                    ? "   ← a node that never fills these = C2 (demo-04)" : ""));
            System.out.println();
        });

        System.out.println("  " + "-".repeat(59));
        System.out.println("  📤  REPORT (structured AgentAnswer — Week 2 contract):");
        System.out.println(Agents.formatReport(state.report));
        System.out.println();
        System.out.println("  🧾  AUDIT TRAIL (recorded by the nodes, with per-step cost):");
        for (AuditRecord m : state.messages) {
            System.out.println("          • " + DemoSupport.compact(m.detail()));
        }
        System.out.printf("  ⚡  TOTAL: %d steps · $%.6f%n", state.steps, state.cost);
        System.out.println();
    }

    private static String trim(String csv) {
        String t = csv.replaceAll(", $", "");
        return t.isEmpty() ? "—" : t;
    }
}