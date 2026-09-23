package devbuddy.scripts.week05;

import devbuddy.config.AppConfig;
import io.modelcontextprotocol.client.McpSyncClient;
import io.modelcontextprotocol.spec.McpSchema;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.Message;
import org.springframework.ai.chat.messages.SystemMessage;
import org.springframework.ai.chat.messages.ToolResponseMessage;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.openai.OpenAiChatOptions;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Week 5 — Demo 5: The Ecosystem Payoff — Prompts, Resources, and Tools.
 *
 * <p>THE POINT: the grand finale. The LLM acts as the orchestrator. It asks
 * the Server for the Prompt, the Resource, and the Tools — then executes the
 * workflow. True separation of Context from the Application layer.</p>
 *
 * <p>Prerequisites: Qdrant running (Week 3) and the MCP server on port 8002.</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week05.Demo05McpWithLlm}</p>
 */
public class Demo05McpWithLlm {

    public static void main(String[] args) {
        McpSyncClient client = null;
        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            ChatModel chatModel = ctx.getBean(ChatModel.class);
            client = DemoSupport.connect();

            DemoSupport.header("Demo 5: The Ecosystem Payoff");
            System.out.println();

            // 1. Get Prompt
            System.out.println("  ── 1. Fetching Server Prompt ───────────────────────");
            String service = "payment-api";
            McpSchema.GetPromptResult prompt = client.getPrompt(
                    new McpSchema.GetPromptRequest("incident_analysis_prompt",
                            Map.of("service_name", service)));
            String systemText = ((McpSchema.TextContent) prompt.messages().get(0).content()).text();
            System.out.println("  Received: '" + systemText.substring(0, Math.min(70, systemText.length())) + "...'");
            System.out.println();

            // 2. Get Resource
            System.out.println("  ── 2. Fetching Server Resource ─────────────────────");
            String resourceText;
            try {
                McpSchema.ReadResourceResult data = client.readResource(
                        new McpSchema.ReadResourceRequest("file://shared/data/payment-api-spec.md"));
                String full = ((McpSchema.TextResourceContents) data.contents().get(0)).text();
                resourceText = full.substring(0, Math.min(100, full.length())) + "...";
            } catch (Exception e) {
                resourceText = "(Resource unavailable)";
            }
            System.out.println("  Received: '" + resourceText + "'");
            System.out.println();

            // 3. Get Tools
            System.out.println("  ── 3. Fetching Server Tools ────────────────────────");
            List<McpSchema.Tool> mcpTools = client.listTools().tools();
            List<ToolCallback> callbacks = new ArrayList<>();
            for (McpSchema.Tool t : mcpTools) {
                callbacks.add(DemoSupport.mcpToolCallback(client, t));
            }
            System.out.println("  Bound " + callbacks.size() + " tools to LLM.");
            System.out.println();

            // 4. Execute
            System.out.println("  ── 4. LLM Execution Loop ───────────────────────────");
            List<Message> messages = new ArrayList<>();
            messages.add(new SystemMessage(systemText));
            messages.add(new UserMessage("Here is the API Spec Resource: " + resourceText
                    + "\n\nPlease proceed with the analysis."));

            for (int turn = 0; turn < 4; turn++) {
                Prompt chatPrompt = new Prompt(messages, OpenAiChatOptions.builder()
                        .toolCallbacks(callbacks)
                        .internalToolExecutionEnabled(false)
                        .build());
                ChatResponse response = chatModel.call(chatPrompt);
                AssistantMessage out = response.getResult().getOutput();
                messages.add(out);

                if (!out.hasToolCalls()) {
                    System.out.println("  [Final Answer]:\n  " + out.getText());
                    break;
                }

                List<ToolResponseMessage.ToolResponse> responses = new ArrayList<>();
                for (AssistantMessage.ToolCall tc : out.getToolCalls()) {
                    System.out.println("  [Model Decided]: Call " + tc.name() + "(" + tc.arguments() + ")");
                    ToolCallback cb = callbacks.stream()
                            .filter(c -> c.getToolDefinition().name().equals(tc.name()))
                            .findFirst().orElseThrow();
                    String result = cb.call(tc.arguments());
                    responses.add(new ToolResponseMessage.ToolResponse(tc.id(), tc.name(), result));
                }
                messages.add(new ToolResponseMessage(responses));
            }

            System.out.println();
            System.out.println(DemoSupport.BORDER);
            System.out.println("  THE MESSAGE: The client is completely generic. The Prompts,");
            System.out.println("  Resources, and Tools all lived on the server. We have achieved");
            System.out.println("  true separation of Context from the Application layer.");
            System.out.println(DemoSupport.BORDER);
        } catch (Exception e) {
            DemoSupport.connectionHint();
            System.out.println("  " + e.getMessage());
        } finally {
            if (client != null) {
                client.closeGracefully();
            }
        }
    }
}
