package devbuddy.scripts.week04;

import devbuddy.config.AppConfig;
import devbuddy.rag.RagService;
import devbuddy.tools.ToolEngine;
import devbuddy.tools.ToolJson;
import org.springframework.ai.chat.messages.SystemMessage;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

import java.util.List;
import java.util.Map;
import java.util.function.Function;

/**
 * Week 4 — Demo 5: RAG as a Tool — a tool is just data with a name.
 *
 * <p>THE POINT: the model does not care whether a tool's data came from a
 * hardcoded dict or your Week-3 vector store. This tool runs
 * {@link RagService#retrieve} + LLM extraction, wrapped in the same registry
 * and executed through the same app layer as every other tool.</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week04.Demo05RagBridge}
 * (requires Qdrant running)</p>
 */
public class Demo05RagBridge {

    public static void main(String[] args) throws Exception {
        System.out.println("=".repeat(70));
        System.out.println("  Demo 5: RAG as a Tool — a tool is just data with a name");
        System.out.println("=".repeat(70));
        System.out.println();

        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            RagService rag = ctx.getBean(RagService.class);
            ChatModel model = ctx.getBean(ChatModel.class);

            rag.indexDocuments(null, 512, 64);
            System.out.println("  ✅ Week-3 index ready");
            System.out.println();
            System.out.println("  get_build_status_from_docs(service_name) → status JSON");
            System.out.println("  data source: RagService.retrieve() (Week 3) + LLM extraction.");
            System.out.println("  Same interface as the dict-backed tool — different data.");
            System.out.println();

            Function<Map<String, Object>, String> docsTool = a -> {
                String service = String.valueOf(a.get("service_name"));
                List<String> chunks = rag.retrieve(service + " build status health deploy", 5);
                if (chunks.isEmpty()) {
                    return ToolJson.toJson(Map.of("status", "unknown",
                            "error", "No docs for '" + service + "'"));
                }
                String context = String.join("\n\n", chunks);
                ChatResponse response = model.call(new Prompt(List.of(
                        new SystemMessage("Extract the build/health status from the context. Return JSON with " +
                                "'status' (healthy/degraded/down/unknown) and 'last_deploy' (timestamp). " +
                                "Only use data from the context."),
                        new UserMessage("Service: " + service + "\n\nContext:\n" + context))));
                String text = response.getResult().getOutput().getText() == null
                        ? "" : response.getResult().getOutput().getText().strip();
                Map<String, Object> parsed = ToolJson.parse(text);
                return parsed.isEmpty() ? text : ToolJson.toJson(parsed);
            };

            Map<String, Function<Map<String, Object>, String>> registry = Map.of(
                    "get_build_status_from_docs", docsTool);
            Map<String, Object> call = Map.of("name", "get_build_status_from_docs",
                    "args", Map.of("service_name", "payment-api"));

            System.out.println("  Compare: the dict says payment-api is DEGRADED. What do the");
            System.out.println("  DOCS say? Run the tool through the same app layer:");
            System.out.println();
            String result = ToolEngine.executeToolSafely(call, 2, registry, false, 0);
            System.out.println("  Tool returned: " + result);
            System.out.println();
        }

        System.out.println("=".repeat(70));
        System.out.println("  THE COMPOSITION PATTERN: a tool is a contract — name + args + JSON");
        System.out.println("  out. Where the data comes from (dict, API, vector store) is an");
        System.out.println("  implementation detail. The orchestrator does not care.");
        System.out.println();
        System.out.println("  YOUR TURN:");
        System.out.println("    • Point a second tool at the docs too — same pattern.");
        System.out.println("    • Add a min_score guard so a weak retrieval returns a");
        System.out.println("      structured 'no match', not a guess.");
        System.out.println("=".repeat(70));
    }
}
