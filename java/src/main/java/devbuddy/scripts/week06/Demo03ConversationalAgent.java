package devbuddy.scripts.week06;

import devbuddy.agent.AgentState;
import devbuddy.agent.Agents;
import devbuddy.config.AppConfig;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

import java.util.Scanner;

/**
 * Demo 3: Conversational Agent — talk to DevBuddy.
 *
 * <p>Type queries. The dynamic agent plans, calls tools, and responds.
 * Type 'quit' to exit, 'cost' to see cumulative spending.</p>
 *
 * <p>Requires: MCP server on :8002 (+ Qdrant for the docs step).</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week06.Demo03ConversationalAgent}</p>
 */
public class Demo03ConversationalAgent {

    public static void main(String[] args) {
        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            Agents agents = ctx.getBean(Agents.class);

            System.out.println("=".repeat(70));
            System.out.println("  DevBuddy Agent — Conversational Mode");
            System.out.println("=".repeat(70));
            System.out.println();
            System.out.println("  I can check build status, deployment history, active");
            System.out.println("  incidents, and retrieve documentation. Ask me anything");
            System.out.println("  about auth-service, payment-api, or inventory-service.");
            System.out.println();
            System.out.println("  Commands:  quit  |  cost  |  help");
            System.out.println();

            DemoSupport.primeIndex(ctx);

            Scanner in = new Scanner(System.in);
            double totalCost = 0.0;
            int turn = 0;

            while (true) {
                System.out.print("  You → ");
                if (!in.hasNextLine()) {
                    break; // EOF (piped input)
                }
                String query = in.nextLine().trim();
                if (query.isEmpty()) {
                    continue;
                }
                String cmd = query.toLowerCase();
                if (cmd.equals("quit") || cmd.equals("exit") || cmd.equals("q")) {
                    System.out.println();
                    System.out.printf("  Session ended. %d queries, total cost ~$%.6f%n",
                            turn, totalCost);
                    System.out.println("=".repeat(70));
                    break;
                }
                if (cmd.equals("cost")) {
                    System.out.printf("  💰 Total cost this session: ~$%.6f%n", totalCost);
                    System.out.println();
                    continue;
                }
                if (cmd.equals("help")) {
                    System.out.println("  Try: 'Is payment-api healthy?'");
                    System.out.println("       'What was deployed recently for auth-service?'");
                    System.out.println("       'Any incidents for inventory-service?'");
                    System.out.println("       'Give me a full readiness report for payment-api'");
                    System.out.println();
                    System.out.println("  Worth poking at:");
                    System.out.println("       'Deploy auth-service to production'");
                    System.out.println("         → no deploy tool exists — the registry refuses");
                    System.out.println("       'What does the payment-api spec say?'");
                    System.out.println("         → docs-only query: the router should skip the tools");
                    System.out.println();
                    continue;
                }

                turn++;
                System.out.printf("  ⏳ Turn %d — planning and executing...%n", turn);
                AgentState result = agents.runDynamicAgent(query);
                totalCost += result.cost;

                System.out.printf("  Steps: %d  |  Cost: ~$%.6f%n", result.steps, result.cost);
                System.out.println("  Path: " + DemoSupport.path(result));
                System.out.println("  ─────────────────────────────────────────────");
                if (!result.error.isEmpty()) {
                    System.out.println("  ⚠️   " + result.error);
                }
                System.out.println(Agents.formatReport(result.report));
                System.out.println();
            }
        }
        System.exit(0);
    }
}