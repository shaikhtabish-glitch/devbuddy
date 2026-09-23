package devbuddy.scripts.week04;

import devbuddy.config.AppConfig;
import devbuddy.tools.ToolCatalog;
import devbuddy.tools.ToolLoop;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

import java.util.ArrayList;
import java.util.List;

/**
 * Week 4 — Demo 2: Tool Routing — two tools, one question.
 *
 * <p>THE POINT: the model picks the tool — but YOUR descriptions taught it
 * to pick. Routing is a design problem, not a model problem.</p>
 *
 * <p>Part A prints the OBSERVED calls per question (they vary run to run).
 * Part B runs one question against VAGUE vs PRECISE descriptions.</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week04.Demo02ToolRouting}</p>
 */
public class Demo02ToolRouting {

    public static void main(String[] args) {
        System.out.println("=".repeat(70));
        System.out.println("  Demo 2: Tool Routing — Observed, then the Description Lever");
        System.out.println("=".repeat(70));
        System.out.println();

        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            ChatModel model = ctx.getBean(ChatModel.class);

            // ── Part A: observed routing over the real tools ──
            System.out.println("  ── Part A: Observed routing (real tools) ────────────────");
            System.out.println();
            String[] questions = {
                    "Is the auth-service healthy?",
                    "What were the last 2 deployments for payment-api?",
                    "Are there any active incidents for inventory-service?",
                    "What's the latest build status?", // deliberately ambiguous
            };
            for (String q : questions) {
                List<String> recorded = new ArrayList<>();
                ToolLoop.run(q, model, ToolCatalog.callbacks(recorded));
                System.out.println("  User: " + q);
                if (recorded.isEmpty()) {
                    System.out.println("       → NO tool called — the model answered directly.");
                } else {
                    for (String exec : recorded) {
                        System.out.println("       → " + exec);
                    }
                }
                System.out.println();
            }
            System.out.println("  Note Q4: no service named. Observe what the model does.");
            System.out.println();

            // ── Part B: the description lever ─────────────────
            System.out.println("  ── Part B: The description lever ────────────────────────");
            System.out.println();
            String questionB = "Is the payment-api healthy and what was deployed most recently?";
            System.out.println("  Question: " + questionB);
            System.out.println();

            List<String> vague = new ArrayList<>();
            ToolLoop.run(questionB, model, ToolCatalog.callbacksVague(vague));
            System.out.println("  VAGUE descriptions:");
            vague.forEach(e -> System.out.println("       → " + e));

            List<String> precise = new ArrayList<>();
            ToolLoop.run(questionB, model, ToolCatalog.callbacks(precise));
            System.out.println("  PRECISE descriptions:");
            precise.forEach(e -> System.out.println("       → " + e));
            System.out.println();
        }

        System.out.println("=".repeat(70));
        System.out.println("  ROUTING IS A DESIGN PROBLEM, NOT A MODEL PROBLEM.");
        System.out.println("  Above are the OBSERVED calls — they vary run to run. The lever");
        System.out.println("  you control is not the model; it is each tool's name and");
        System.out.println("  description. Vague description → vague routing.");
        System.out.println("=".repeat(70));
    }
}
