package devbuddy.scripts.week05;

import io.modelcontextprotocol.client.McpClient;
import io.modelcontextprotocol.client.McpSyncClient;
import io.modelcontextprotocol.client.transport.HttpClientSseClientTransport;
import io.modelcontextprotocol.spec.McpSchema;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.ai.tool.function.FunctionToolCallback;
import org.springframework.core.ParameterizedTypeReference;
import reactor.core.publisher.Hooks;

import java.time.Duration;
import java.util.Map;

/**
 * Week 5 — shared helpers for the MCP demos (Java).
 *
 * <p>Connects an MCP client to the DevBuddy MCP server over SSE using the
 * JDK HttpClient-based transport (no extra web dependencies on the client).</p>
 */
public final class DemoSupport {

    /** MCP server base URL (SSE endpoint is appended by the transport). */
    public static final String BASE_URL =
            System.getenv().getOrDefault("MCP_URL", "http://127.0.0.1:8002");

    public static final String BORDER = "=".repeat(70);

    static {
        // The SSE transport's reactor pipeline logs a dropped-error stack trace
        // when a connection fails (e.g. demo-03 Act 3). Keep demo output clean.
        Hooks.onErrorDropped(e -> { });
        try {
            for (String name : new String[]{"reactor", "reactor.core", "io.modelcontextprotocol"}) {
                ((ch.qos.logback.classic.Logger) org.slf4j.LoggerFactory.getLogger(name))
                        .setLevel(ch.qos.logback.classic.Level.OFF);
            }
        } catch (Exception ignored) {
            // logback not on the classpath — the hook above still applies
        }
    }

    private DemoSupport() {
    }

    /** Connect and initialize an MCP client to the default server. */
    public static McpSyncClient connect() {
        return connect(BASE_URL);
    }

    /** Connect and initialize an MCP client to the given base URL. */
    public static McpSyncClient connect(String baseUrl) {
        HttpClientSseClientTransport transport = HttpClientSseClientTransport
                .builder(baseUrl)
                .sseEndpoint("/sse")
                .build();
        McpSyncClient client = McpClient.sync(transport)
                .requestTimeout(Duration.ofSeconds(180))
                .clientInfo(new McpSchema.Implementation("devbuddy-demo-client", "1.0.0"))
                .build();
        if (!client.isInitialized()) {
            client.initialize();
        }
        return client;
    }

    /** Print a bordered title, matching the other weeks' demo style. */
    public static void header(String title) {
        System.out.println(BORDER);
        System.out.println("  " + title);
        System.out.println(BORDER);
    }

    /**
     * Pause so the learner can predict before the reveal.
     * No-op when there is no interactive console (CI / piped runs).
     */
    public static void pause(String prompt) {
        var console = System.console();
        if (console == null) {
            return;
        }
        console.readLine(prompt);
    }

    /** Print a helpful hint when the server can't be reached. */
    public static void connectionHint() {
        System.err.println("  ❌ Could not connect to the MCP server at " + BASE_URL);
        System.err.println("  Start it first:  mvn -q compile exec:java -Dexec.mainClass=devbuddy.mcp.DevBuddyMcpServer");
    }

    /**
     * Wrap an MCP tool as a Spring AI {@link ToolCallback} whose schema is the
     * server's own JSON schema (so the model sees the real contract).
     */
    public static ToolCallback mcpToolCallback(McpSyncClient client, McpSchema.Tool tool) {
        String schemaJson;
        try {
            schemaJson = new ObjectMapper().writeValueAsString(tool.inputSchema());
        } catch (Exception e) {
            schemaJson = "{\"type\":\"object\"}";
        }
        String description = tool.description() == null ? tool.name() : tool.description();
        String name = tool.name();
        return FunctionToolCallback
                .<Map<String, Object>, String>builder(name, args -> {
                    McpSchema.CallToolResult res = client.callTool(
                            new McpSchema.CallToolRequest(name, args));
                    return res.content().isEmpty() ? ""
                            : ((McpSchema.TextContent) res.content().get(0)).text();
                })
                .description(description)
                .inputSchema(schemaJson)
                .inputType(new ParameterizedTypeReference<Map<String, Object>>() {
                })
                .build();
    }
}
