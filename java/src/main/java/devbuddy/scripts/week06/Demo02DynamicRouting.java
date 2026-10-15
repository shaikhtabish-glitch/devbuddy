package devbuddy.scripts.week06;

import devbuddy.agent.AgentState;
import devbuddy.agent.Agents;
import devbuddy.agent.AuditRecord;
import devbuddy.agent.Graph;
import devbuddy.config.AppConfig;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

/**
 * Demo 2: Dynamic Routing — the model PROPOSES, the registry disposes.
 *
 * <p>Runs the dynamic agent on 3 queries and prints, for every planning
 * decision: what the model proposed, what the code accepted/rejected, and
 * why. That proposal→decision stream — not the step list — is the lesson.
 * Also measures fixed vs dynamic on the same query (steps + cost).</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week06.Demo02DynamicRouting}</p>
 */
public class Demo02DynamicRouting {

    public static void main(String[] args) {
        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            Agents agents = ctx.getBean(Agents.class);

            DemoSupport.header("Demo 2: Dynamic Routing — LLM proposes, registry disposes");
            System.out.println();
            System.out.println("  The graph's ROUTES are still static; which route is taken at");
            System.out.println("  runtime comes from a planning node. The model may only propose");
            System.out.println("  steps the registry allows for this query's category — watch the");
            System.out.println("  decisions below: accepted, corrected, or handed to the guard.");
            System.out.println();

            DemoSupport.primeIndex(ctx);

            Object[][] queries = {
                    {"Is payment-api healthy?", "health only"},
                    {"What was deployed recently for payment-api and are there any incidents?",
                            "multi-intent (deploys + incidents)"},
                    {"Give me a full readiness assessment for payment-api.", "full assessment"},
            };

            for (int i = 0; i < queries.length; i++) {
                String query = (String) queries[i][0];
                System.out.println("  ── " + queries[i][1] + " ──");
                System.out.println("  📥  QUERY: \"" + query + "\"");
                AgentState result = agents.runDynamicAgent(query);

                System.out.printf("  ⚡  Steps: %d  |  Cost: $%.6f%n", result.steps, result.cost);
                System.out.println("  🔀  Path:   " + DemoSupport.path(result));
                showPlans(result);
                if (!result.error.isEmpty()) {
                    System.out.println("  ⚠️   Error:  " + result.error);
                }
                System.out.println("  " + "-".repeat(59));
                System.out.println(Agents.formatReport(result.report));
                System.out.println();

                if (i == 0) {
                    System.out.println("  📊  SAME query through demo-01's fixed chain:");
                    AgentState fixed = agents.runFixedChain(query);
                    System.out.printf("      fixed   : %d steps · $%.6f%n", fixed.steps, fixed.cost);
                    System.out.printf("      dynamic : %d steps · $%.6f%n", result.steps, result.cost);
                    System.out.println("      → dynamic pays for planning LLM calls; fixed pays for");
                    System.out.println("        running its steps whether you needed them or not.");
                    System.out.println();
                }
            }

            System.out.println(DemoSupport.BORDER);
            System.out.println("  What varied between the three queries? Not the graph — the");
            System.out.println("  PLAN decisions. Same nodes, same edges, different runtime path,");
            System.out.println("  different cost. Measure your own: take-home Part A runs 5");
            System.out.println("  queries through both and compares.");
            System.out.println(DemoSupport.BORDER);
            System.out.println();
        }
        System.exit(0);
    }

    /** The plan decisions (LLM proposes → code disposes), from the audit trail. */
    private static void showPlans(AgentState result) {
        boolean any = result.messages.stream().anyMatch(m -> "plan".equals(m.step()));
        if (!any) {
            return;
        }
        System.out.println("      🧠  plan decisions (LLM proposes → code disposes):");
        for (AuditRecord p : result.messages) {
            if (!"plan".equals(p.step())) {
                continue;
            }
            String proposal = p.getString("proposal");
            if (proposal == null) {
                proposal = "—";
            }
            String decision = p.getString("decision");
            if (decision == null) {
                decision = "?";
            }
            String reason = p.getString("reason");
            String corrected = p.getString("corrected_to");
            String marker = "accept".equals(decision) ? "✅" : "⚠️ ";
            String dispatched = (corrected != null && !corrected.equals(proposal))
                    ? "  → dispatched: " + corrected : "";
            System.out.printf("         %s proposed %s → %s%s  · $%.6f%s%n",
                    marker, proposal, decision,
                    reason != null ? "  (" + reason + ")" : "",
                    p.cost(), dispatched);
        }
    }
}