package devbuddy.agent;

import com.fasterxml.jackson.databind.JsonNode;
import devbuddy.schemas.Json;
import devbuddy.tools.ToolData;
import io.modelcontextprotocol.client.McpClient;
import io.modelcontextprotocol.client.McpSyncClient;
import io.modelcontextprotocol.client.transport.HttpClientSseClientTransport;
import io.modelcontextprotocol.spec.McpSchema;
import reactor.core.publisher.Hooks;

import java.time.Duration;
import java.util.Map;

/**
 * The {@code call_tool} seam — Python's {@code TOOL_BACKEND} ported to Java.
 *
 * <p>Same tool <em>name</em> on both backends; the transport differs:</p>
 * <ul>
 *   <li>{@code TOOL_BACKEND=mcp} (default) — Week 5 server over SSE
 *       (port 8002, like the demos), connected lazily.</li>
 *   <li>{@code TOOL_BACKEND=local} — Week 4 {@link ToolData} in-process
 *       (no server needed — what the agent tests use).</li>
 * </ul>
 *
 * <p>Failures are {@link ToolFailure}s — structured, never a crash; the node
 * that called the tool records them in the audit trail.</p>
 */
public interface ToolBackend {

    /** Raw JSON text, or {@link ToolFailure} on transport/failure payloads. */
    String call(String toolName, Map<String, Object> args);

    /** Backend from system property (tests) or env (demos) — default mcp. */
    static ToolBackend fromEnv() {
        String backend = System.getProperty("TOOL_BACKEND");
        if (backend == null || backend.isBlank()) {
            backend = System.getenv().getOrDefault("TOOL_BACKEND", "mcp");
        }
        return "local".equalsIgnoreCase(backend.trim())
                ? new LocalBackend()
                : new McpBackend();
    }

    /** Failure payload detection — same shape as Python's _looks_like_failure. */
    static boolean looksLikeFailure(String raw) {
        try {
            JsonNode data = Json.MAPPER.readTree(raw);
            if (data.has("status") && "failed".equals(data.get("status").asText())) {
                return true;
            }
            return data.has("error") && !data.has("status");
        } catch (Exception e) {
            return true; // unparseable = failure
        }
    }

    /** Week 4 — in-process tools (no transport at all). */
    final class LocalBackend implements ToolBackend {
        @Override
        public String call(String toolName, Map<String, Object> args) {
            String service = String.valueOf(args.getOrDefault("service_name", "payment-api"));
            int limit = args.get("limit") instanceof Number n ? n.intValue() : 3;
            String raw = switch (toolName) {
                case "get_build_status" -> ToolData.buildStatus(service);
                case "get_recent_deploys" -> ToolData.recentDeploys(service, limit);
                case "get_active_incidents" -> ToolData.activeIncidents(service);
                default -> "{\"error\": \"unknown tool: " + toolName + "\"}";
            };
            if (looksLikeFailure(raw)) {
                throw new ToolFailure(toolName + ": " + raw);
            }
            return raw;
        }
    }

    /** Week 5 — SSE client to the long-lived server (lazily connected). */
    final class McpBackend implements ToolBackend {

        private static final String BASE_URL =
                firstNonBlank(System.getProperty("MCP_URL"),
                        System.getenv().getOrDefault("MCP_URL", "http://127.0.0.1:8002"));

        static {
            // Same cleanup as DemoSupport: the SSE reactor pipeline logs a
            // dropped-error stack trace when a connection fails.
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

        private McpSyncClient client;

        private static String firstNonBlank(String a, String b) {
            return (a != null && !a.isBlank()) ? a : b;
        }

        private synchronized McpSyncClient client() {
            if (client == null || !client.isInitialized()) {
                var transport = HttpClientSseClientTransport.builder(BASE_URL)
                        .sseEndpoint("/sse")
                        .build();
                McpSyncClient c = McpClient.sync(transport)
                        .requestTimeout(Duration.ofSeconds(30))
                        .clientInfo(new McpSchema.Implementation("devbuddy-agent", "1.0.0"))
                        .build();
                try {
                    c.initialize();
                } catch (Exception e) {
                    throw new ToolFailure("MCP server unreachable at " + BASE_URL
                            + " — start it: mvn -q compile exec:java"
                            + " -Dexec.mainClass=devbuddy.mcp.DevBuddyMcpServer ("
                            + e.getMessage() + ")");
                }
                client = c;
            }
            return client;
        }

        @Override
        public String call(String toolName, Map<String, Object> args) {
            try {
                McpSchema.CallToolResult result = client()
                        .callTool(new McpSchema.CallToolRequest(toolName, args));
                String text = result.content().isEmpty() ? ""
                        : ((McpSchema.TextContent) result.content().get(0)).text();
                if (result.isError() != null && result.isError()) {
                    throw new ToolFailure(toolName + ": " + text);
                }
                if (looksLikeFailure(text)) {
                    throw new ToolFailure(toolName + ": " + text);
                }
                return text;
            } catch (ToolFailure e) {
                throw e;
            } catch (Exception e) {
                throw new ToolFailure(toolName + ": " + e.getMessage());
            }
        }
    }
}