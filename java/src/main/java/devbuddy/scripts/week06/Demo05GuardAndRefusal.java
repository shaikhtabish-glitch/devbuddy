package devbuddy.scripts.week06;

import devbuddy.agent.AgentState;
import devbuddy.agent.Agents;
import devbuddy.agent.AuditRecord;
import devbuddy.agent.Budget;
import devbuddy.config.AppConfig;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

/**
 * Demo 5 (C3): Guards — the agent knows when to stop.
 *
 * <ul>
 *   <li>Test 1: guarded chain WITH check_build → validity guard PASSES → report</li>
 *   <li>Test 2: same query, check_build removed → guard BLOCKS (typed answer,
 *       zero LLM spend on a report — proven by the cost line)</li>
 *   <li>Test 3: refusal — "Deploy ..." → registry-driven refusal</li>
 *   <li>Test 4: budget guard — maxSteps forced to 2 → typed stop, not a runaway</li>
 * </ul>
 *
 * <p>Requires: MCP server (:8002) + Qdrant; test 3 needs only the LLM.</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week06.Demo05GuardAndRefusal}</p>
 */
public class Demo05GuardAndRefusal {

    private static final String HEALTHY_QUERY = "Is auth-service healthy?";

    public static void main(String[] args) {
        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            Agents agents = ctx.getBean(Agents.class);

            DemoSupport.header("Demo 5 (C3): Validity Guard + Refusal + Budget");
            System.out.println();
            System.out.println("  Three guards, three jobs: validity (state must be acceptable),");
            System.out.println("  structural (registry decides what's possible), budget (steps/cost");
            System.out.println("  ceiling). All three produce TYPED answers — no LLM, no prose.");
            System.out.println();

            DemoSupport.primeIndex(ctx);

            // ── Test 1: validity guard PASSES when required data present ──
            System.out.println("  ── Test 1: build checked → guard PASSES → report generated ──");
            // auth-service: latest deploy success, incident resolved — unambiguous
            // ground truth, so this pass-path is stable across runs.
            System.out.println("  📥  QUERY: \"" + HEALTHY_QUERY + "\"");
            AgentState r1 = show(agents.runGuardedChain(HEALTHY_QUERY, true));

            // ── Test 2: validity guard STOPS when required data missing ───
            System.out.println("  ── Test 2: check_build REMOVED → guard STOPS the agent ──");
            System.out.println("  📥  QUERY: \"" + HEALTHY_QUERY + "\"");
            AgentState r2 = show(agents.runGuardedChain(HEALTHY_QUERY, false));

            System.out.printf("  💰  COST PROOF: test 1 = $%.6f  |  test 2 = $%.6f%n",
                    r1.cost, r2.cost);
            System.out.println("      generate_report in test 2's path? "
                    + (r2.path().contains("generate_report")
                    ? "YES (unexpected!)" : "NO — the guard wrote"));
            System.out.println("      the blocked answer in CODE. A guard that spends tokens");
            System.out.println("      isn't a guard, it's a suggestion.");
            System.out.println();

            // ── Test 3: refusal — no deploy tool exists ───────────────────
            System.out.println("  ── Test 3: 'Deploy ...' → refused from the registry ──");
            String deployQuery = "Deploy auth-service to production";
            System.out.println("  📥  QUERY: \"" + deployQuery + "\"");
            AgentState r3 = show(agents.runDynamicAgent(deployQuery));
            for (AuditRecord m : r3.messages) {
                if ("plan".equals(m.step())) {
                    System.out.printf("  🧠  plan: proposal=%s → %s  (%s)%n",
                            m.getString("proposal"), m.getString("decision"),
                            m.getString("reason") != null ? m.getString("reason")
                                    : "registry lookup");
                }
            }
            System.out.println("  The refusal message lists ONLY registry entries — the model");
            System.out.println("  never got to invent what the agent can do.");
            System.out.println();

            // ── Test 4: budget guard — stop a runaway run ─────────────────
            System.out.println("  ── Test 4: budget guard — maxSteps forced to 2 ──");
            String budgetQuery = "Give me a full readiness assessment for payment-api.";
            System.out.println("  📥  QUERY: \"" + budgetQuery + "\"");
            System.out.println("  🔧  maxSteps: " + Budget.maxSteps + " → 2 (temporarily)");

            int savedSteps = Budget.maxSteps;
            AgentState r4;
            Budget.maxSteps = 2;
            try {
                r4 = agents.runDynamicAgent(budgetQuery);
            } finally {
                Budget.maxSteps = savedSteps;
            }

            System.out.println("  🔀  Path: " + DemoSupport.path(r4));
            System.out.printf("  ⚡  Steps: %d (limit was 2)  |  next_step=%s%n",
                    r4.steps, r4.nextStep);
            System.out.println("  " + "-".repeat(59));
            System.out.println(Agents.formatReport(r4.report));
            System.out.printf("  💰  cost: $%.6f — stopped BEFORE burning the budget;%n", r4.cost);
            System.out.println("      the blocked answer cost 0 tokens (typed, not generated).");
            System.out.println();
            System.out.println("  🔧  maxSteps restored to " + Budget.maxSteps + ".");
            System.out.println(DemoSupport.BORDER);
            System.out.println();
        }
        System.exit(0);
    }

    private static AgentState show(AgentState result) {
        System.out.println("  🔀  Path: " + DemoSupport.path(result));
        System.out.println("  [state] build_status = \"" + result.buildStatus + "\"");
        // The guard's DECISION is in the audit — print it, don't infer it.
        for (AuditRecord m : result.messages) {
            if ("validate".equals(m.step())) {
                if ("passed".equals(m.getString("status"))) {
                    System.out.println("  🛡  PASS → model may generate the report");
                } else {
                    System.out.println("  🛑 BLOCKED (" + m.getString("category") + ")");
                }
            }
        }
        if (!result.error.isEmpty()) {
            System.out.println("  🛑  " + result.error);
        }
        System.out.println("  " + "-".repeat(59));
        System.out.println(Agents.formatReport(result.report));
        System.out.printf("  💰  cost so far: $%.6f%n", result.cost);
        System.out.println();
        return result;
    }
}