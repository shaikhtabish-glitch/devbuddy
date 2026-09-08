package devbuddy.scripts.week04;

import devbuddy.config.AppConfig;
import devbuddy.tools.ToolCatalog;
import devbuddy.tools.ToolEngine;
import devbuddy.tools.ToolLoop;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

import java.util.ArrayList;
import java.util.List;

/**
 * Week 4 — Demo 4: Full tool loop — trace, audit, and the bill.
 *
 * <p>THE POINT: every tool call is a decision you can replay and a bill you
 * can read. If you cannot trace it, do not ship it. Each query records every
 * executed tool and its token usage; the loop is bounded by
 * {@link ToolEngine#MAX_TOOL_TURNS} because a runaway tool loop is a cost
 * event, not a feature.</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week04.Demo04FullTrace}</p>
 */
public class Demo04FullTrace {

    public static void main(String[] args) {
        System.out.println("=".repeat(70));
        System.out.println("  Demo 4: Full Tool Loop — Trace, Audit, and Cost");
        System.out.println("=".repeat(70));
        System.out.println();
        System.out.println("  The trace is the audit log: who decided, what executed, what it");
        System.out.println("  returned — and how many tokens each decision cost.");
        System.out.println();

        String[] queries = {
                "Is the auth-service healthy?",
                "What were the last 2 deployments for payment-api?",
                "Is payment-api healthy, what was deployed recently, and are there active incidents?",
        };

        long totalIn = 0, totalOut = 0, totalTok = 0;
        int totalCalls = 0;

        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            ChatModel model = ctx.getBean(ChatModel.class);

            for (String query : queries) {
                List<String> recorded = new ArrayList<>();
                ToolLoop.RunResult result = ToolLoop.run(query, model, ToolCatalog.callbacks(recorded));

                System.out.println("  QUERY: " + query);
                for (String exec : recorded) {
                    System.out.println("    [EXECUTE] " + exec);
                }
                System.out.println("    [ANSWER]  " + result.answer());
                System.out.printf("    → %d tool(s); %d in / %d out / %d total tokens%n%n",
                        recorded.size(), result.inputTokens(), result.outputTokens(), result.totalTokens());
                totalIn += result.inputTokens();
                totalOut += result.outputTokens();
                totalTok += result.totalTokens();
                totalCalls += recorded.size();
            }
        }

        System.out.println("=".repeat(70));
        System.out.println("  THE MESSAGE: the trace is your audit log. If you cannot trace a");
        System.out.println("  decision, you should not ship it. Each round is another LLM call,");
        System.out.println("  so the loop is bounded: a model that never stops calling tools is");
        System.out.println("  a cost event, not a feature.");
        System.out.println();
        System.out.printf("  This run: %d tool executions, %d total tokens.%n", totalCalls, totalTok);
        System.out.println("  MAX_TOOL_TURNS = " + ToolEngine.MAX_TOOL_TURNS + " per query.");
        System.out.println();
        System.out.println("  YOUR TURN:");
        System.out.println("    • Price these tokens at your model's rate × 1,000 users.");
        System.out.println("    • Run a question that needs NO tool and compare the bill.");
        System.out.println("=".repeat(70));
    }
}
