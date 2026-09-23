package devbuddy.scripts.week05;

import com.fasterxml.jackson.databind.ObjectMapper;
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
import org.springframework.ai.tool.function.FunctionToolCallback;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.core.ParameterizedTypeReference;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

/**
 * Week 5 — Demo 2: Advanced Client Patterns (Real Implementation).
 *
 * <p>THE POINT: we don't simulate Progressive Tool Discovery — we build it.
 * The LLM starts with only ONE tool ({@code search_tools}). When it searches,
 * the client queries the MCP server's cached tool list, dynamically converts
 * the matched MCP JSON schemas into Spring AI {@link ToolCallback}s, and
 * resumes the manual tool loop.</p>
 *
 * <p>Prerequisites: MCP server running on port 8002.</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week05.Demo02ClientScaling}</p>
 */
public class Demo02ClientScaling {

    /** Input for the search_tools meta-tool. */
    public record ToolSearchArgs(String query) {
    }

    public static void main(String[] args) {
        McpSyncClient client = null;
        ObjectMapper mapper = new ObjectMapper();

        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            ChatModel chatModel = ctx.getBean(ChatModel.class);
            client = DemoSupport.connect();

            DemoSupport.header("Demo 2: Real Progressive Tool Discovery (Client Scaling)");
            System.out.println();

            System.out.println("  [CLIENT] Synchronizing tool registry from Context Server...");
            List<McpSchema.Tool> mcpTools = client.listTools().tools();
            System.out.println("  [CLIENT] Discovered " + mcpTools.size()
                    + " tools. (Imagine this is 10,000 tools in an enterprise).");
            System.out.println("  [CLIENT] ⚠️ Loading 10,000 JSON schemas would cost ~1.5M tokens per request.");
            System.out.println("  [CLIENT] 🛡️ Strategy: Starting LLM with ONLY ONE tool -> 'search_tools'.");
            System.out.println();

            List<ToolCallback> active = new ArrayList<>();

            final McpSyncClient mcp = client;
            FunctionToolCallback<ToolSearchArgs, String> searchTools = FunctionToolCallback
                    .<ToolSearchArgs, String>builder("search_tools", a -> {
                        System.out.println("\n  [CLIENT] Intercepted LLM request to search cache for: '"
                                + a.query() + "'");
                        String[] words = a.query().toLowerCase().split("\\s+");
                        List<String> names = new ArrayList<>();

                        for (McpSchema.Tool mt : mcpTools) {
                            String nameDesc = (mt.name() + " "
                                    + (mt.description() == null ? "" : mt.description())).toLowerCase();
                            if (Arrays.stream(words).noneMatch(nameDesc::contains)) {
                                continue;
                            }
                            if (active.stream().anyMatch(c ->
                                    c.getToolDefinition().name().equals(mt.name()))) {
                                continue;
                            }

                            String schemaJson;
                            try {
                                schemaJson = mapper.writeValueAsString(mt.inputSchema());
                            } catch (Exception e) {
                                schemaJson = "{\"type\":\"object\"}";
                            }

                            final String toolName = mt.name();
                            final String toolDesc = mt.description() == null ? mt.name() : mt.description();
                            FunctionToolCallback<Map<String, Object>, String> cb = FunctionToolCallback
                                    .<Map<String, Object>, String>builder(toolName, toolArgs -> {
                                        McpSchema.CallToolResult res = mcp.callTool(
                                                new McpSchema.CallToolRequest(toolName, toolArgs));
                                        return res.content().isEmpty() ? ""
                                                : ((McpSchema.TextContent) res.content().get(0)).text();
                                    })
                                    .description(toolDesc)
                                    .inputSchema(schemaJson)
                                    .inputType(new ParameterizedTypeReference<Map<String, Object>>() {
                                    })
                                    .build();

                            active.add(cb);
                            names.add(toolName);

                            System.out.println("  [CLIENT] 💉 DYNAMIC INJECTION: Binding schema for '"
                                    + toolName + "' to LLM context:");
                            System.out.println("  " + "-".repeat(50));
                            System.out.println("  " + schemaJson);
                            System.out.println("  " + "-".repeat(50));
                        }

                        if (names.isEmpty()) {
                            return "No tools found matching your query.";
                        }
                        return "Found and loaded schemas for: " + names
                                + ". You can now call them directly in your next turn.";
                    })
                    .description("Search for available tools on the server and automatically load their schemas.")
                    .inputType(ToolSearchArgs.class)
                    .build();

            active.add(searchTools);

            List<Message> messages = new ArrayList<>();
            messages.add(new SystemMessage(
                    "You are an agent. You start with NO domain tools loaded. You MUST use `search_tools` "
                            + "to find what you need. After searching, the schemas will be loaded "
                            + "and you can call them."));
            messages.add(new UserMessage("What is the build status of the payment-api?"));

            System.out.println("  [INPUT]: What is the build status of the payment-api?");

            for (int turn = 1; turn <= 5; turn++) {
                System.out.println("  ── LLM Orchestration Loop (Turn " + turn + ") ─────────────────");

                Prompt prompt = new Prompt(messages, OpenAiChatOptions.builder()
                        .toolCallbacks(new ArrayList<>(active))
                        .internalToolExecutionEnabled(false)
                        .build());

                ChatResponse response = chatModel.call(prompt);
                AssistantMessage out = response.getResult().getOutput();
                messages.add(out);

                if (!out.hasToolCalls()) {
                    System.out.println("\n  [OUTPUT]: " + out.getText());
                    break;
                }

                List<ToolResponseMessage.ToolResponse> responses = new ArrayList<>();
                for (AssistantMessage.ToolCall tc : out.getToolCalls()) {
                    System.out.println("  [LLM] Decided to use tool: " + tc.name() + "(" + tc.arguments() + ")");
                    ToolCallback cb = active.stream()
                            .filter(c -> c.getToolDefinition().name().equals(tc.name()))
                            .findFirst().orElseThrow();
                    String result = cb.call(tc.arguments());
                    if (!tc.name().equals("search_tools")) {
                        System.out.println("  [SERVER] Result: " + result.strip());
                    }
                    responses.add(new ToolResponseMessage.ToolResponse(tc.id(), tc.name(), result));
                }
                messages.add(new ToolResponseMessage(responses));
                System.out.println();
            }

            System.out.println();
            System.out.println(DemoSupport.BORDER);
            System.out.println("  THE PAYOFF: an AI navigated a large API surface by searching,");
            System.out.println("  discovering, and binding JSON schemas to itself AT RUNTIME,");
            System.out.println("  saving millions of tokens per request.");
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
