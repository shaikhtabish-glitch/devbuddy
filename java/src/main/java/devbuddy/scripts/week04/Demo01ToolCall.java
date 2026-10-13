package devbuddy.scripts.week04;

import devbuddy.config.AppConfig;
import devbuddy.tools.ToolCatalog;
import devbuddy.tools.ToolLoop;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

import java.util.ArrayList;
import java.util.List;

/**
 * Week 4 — Demo 1: Tool Call — wire a tool, watch the model call it.
 *
 * <p>THE POINT: the model could NOT have run the tool. It produced a request
 * ({@code name, args}); Spring AI's tool-calling manager invoked OUR callback
 * (the application layer). The model proposes. Your code disposes.</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week04.Demo01ToolCall}</p>
 */
public class Demo01ToolCall {

    public static void main(String[] args) {
        System.out.println("=".repeat(70));
        System.out.println("  Demo 1: Wire a Tool → Watch the Model Call It");
        System.out.println("=".repeat(70));
        System.out.println();
        System.out.println("  The model sees get_build_status as a schema — a description of a");
        System.out.println("  function it MAY ask for. It never sees the implementation.");
        System.out.println();

        String question = "Is the payment-api healthy?";
        System.out.println("  User: " + question);
        System.out.println();

        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            ChatModel model = ctx.getBean(ChatModel.class);
            List<String> recorded = new ArrayList<>();
            ToolLoop.RunResult result = ToolLoop.run(
                    question, model, ToolCatalog.callbacks(recorded));

            for (String exec : recorded) {
                System.out.println("  → executed: " + exec);
            }
            System.out.println();
            System.out.println("  Model: " + result.answer());
            System.out.println();
        }

        System.out.println("=".repeat(70));
        System.out.println("  THE BOUNDARY: the model could NOT have run get_build_status.");
        System.out.println("  It returned a request. YOUR code (the ToolCallback + registry)");
        System.out.println("  decided whether it became an action — and kept the trace.");
        System.out.println("  The model proposes. Your code disposes.");
        System.out.println("=".repeat(70));
    }
}
