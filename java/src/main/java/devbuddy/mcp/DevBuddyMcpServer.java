package devbuddy.mcp;

import com.fasterxml.jackson.databind.ObjectMapper;
import devbuddy.config.AppConfig;
import devbuddy.rag.RagService;
import io.modelcontextprotocol.server.McpServer;
import io.modelcontextprotocol.server.McpServerFeatures.SyncPromptSpecification;
import io.modelcontextprotocol.server.McpServerFeatures.SyncResourceSpecification;
import io.modelcontextprotocol.server.McpServerFeatures.SyncToolSpecification;
import io.modelcontextprotocol.server.McpSyncServer;
import io.modelcontextprotocol.server.transport.WebFluxSseServerTransportProvider;
import io.modelcontextprotocol.spec.McpSchema;
import io.modelcontextprotocol.spec.McpSchema.CallToolResult;
import io.modelcontextprotocol.spec.McpServerTransportProvider;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.openai.OpenAiChatOptions;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.http.server.reactive.ReactorHttpHandlerAdapter;
import org.springframework.web.reactive.function.server.RouterFunction;
import org.springframework.web.reactive.function.server.RouterFunctions;
import reactor.netty.DisposableServer;
import reactor.netty.http.server.HttpServer;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Week 5 — MCP Server: Shared Tool Ecosystem (Java).
 *
 * <p>Mirrors {@code src/mcp_server.py} / {@code src/mcp_server.js}. Exposes
 * three MCP primitives over SSE:</p>
 * <ul>
 *   <li><b>Tools</b> — get_build_status / get_recent_deploys /
 *       get_active_incidents, plus the destructive delete_incident_record
 *       (token-gated). Each synthesis tool retrieves from the Week 3 RAG
 *       index (Qdrant) and extracts JSON with the LLM.</li>
 *   <li><b>Resources</b> — {@code file://shared/data/{filename}} — read the
 *       shared markdown documents.</li>
 *   <li><b>Prompts</b> — incident_analysis_prompt — the standard SRE
 *       workflow.</li>
 * </ul>
 *
 * <p>Write once. Any MCP client in any language can discover and call these.
 * Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.mcp.DevBuddyMcpServer}</p>
 */
public class DevBuddyMcpServer {

    /** Default SSE port (Python 8000, Node.js 3001, Java 8002). */
    public static final int DEFAULT_PORT = 8002;

    /** Out-of-band Human-In-The-Loop approval token for the destructive tool. */
    public static final String ADMIN_TOKEN = "super-secret-approval-123";

    private static final Path SHARED_DATA_DIR = Path.of("..", "shared", "data");
    private static final String RESOURCE_URI_PREFIX = "file://shared/data/";

    private final RagService rag;
    private final ChatClient chatClient;
    private final String model;
    final ObjectMapper mapper = new ObjectMapper();

    /** Per-tool sliding-window rate-limit state. */
    private final Map<String, RateWindow> rateLimits = new ConcurrentHashMap<>();

    public DevBuddyMcpServer(RagService rag, ChatClient chatClient, String model) {
        this.rag = rag;
        this.chatClient = chatClient;
        this.model = model;
    }

    // ─── Rate limiting ────────────────────────────────────────

    private static final class RateWindow {
        int count;
        long windowStart;
    }

    /**
     * Enforce a per-tool sliding window. Throws {@link RateLimitExceeded}
     * when the caller exceeds {@code limit} calls within {@code windowSeconds}.
     */
    public void checkRateLimit(String toolName, int limit, int windowSeconds) {
        long now = System.currentTimeMillis();
        RateWindow w = rateLimits.computeIfAbsent(toolName, k -> {
            RateWindow r = new RateWindow();
            r.windowStart = now;
            return r;
        });
        if (now - w.windowStart > windowSeconds * 1000L) {
            w.count = 1;
            w.windowStart = now;
        } else {
            w.count++;
            if (w.count > limit) {
                throw new RateLimitExceeded(
                        "RateLimitExceeded: Tool '" + toolName + "' called too many times. "
                                + "Limit " + limit + " per " + windowSeconds + "s.");
            }
        }
    }

    /** Test helper — clear all rate-limit windows. */
    public void resetRateLimits() {
        rateLimits.clear();
    }

    /** Raised when a tool exceeds its rate limit (returned as an isError result). */
    public static class RateLimitExceeded extends RuntimeException {
        public RateLimitExceeded(String message) {
            super(message);
        }
    }

    // ─── Synthesis (retrieve + LLM JSON extraction) ───────────

    /**
     * Retrieve relevant chunks and synthesise structured JSON with the LLM.
     * Never throws: any failure becomes a structured {@code unknown} result
     * the client can always parse (mirrors Python's {@code _synthesise}).
     */
    public String synthesise(String instructions, String query, int k) {
        try {
            List<String> chunks = rag.retrieve(query, k);
            String context = chunks.isEmpty() ? "(no data found)" : String.join("\n\n---\n\n", chunks);

            String system = "You are a data extraction tool. "
                    + "Only use data present in the provided context. Do not invent information. "
                    + "Return ONLY valid JSON (object or array) — no markdown, no prose.\n\n"
                    + "If no relevant data is found, return: "
                    + "{\"status\": \"unknown\", \"reason\": \"no matching data found\"}.\n\n"
                    + instructions;

            String text = chatClient.prompt()
                    .system(system)
                    .user("Context:\n" + context)
                    .options(OpenAiChatOptions.builder().model(model).temperature(0.0).build())
                    .call()
                    .content();
            text = stripFences(text == null ? "" : text.strip());
            mapper.readTree(text); // validate — fall through to catch on failure
            return text;
        } catch (Exception e) {
            return toJson(Map.of(
                    "status", "unknown",
                    "reason", "tool error: " + e.getClass().getSimpleName() + " — " + e.getMessage()));
        }
    }

    private static String stripFences(String text) {
        if (text.startsWith("```")) {
            int nl = text.indexOf('\n');
            text = nl >= 0 ? text.substring(nl + 1) : text.substring(3);
            if (text.endsWith("```")) {
                text = text.substring(0, text.length() - 3).strip();
            }
        }
        return text;
    }

    String toJson(Object value) {
        try {
            return mapper.writeValueAsString(value);
        } catch (Exception e) {
            return "{\"status\":\"unknown\",\"reason\":\"serialization error\"}";
        }
    }

    // ─── Tool handlers ────────────────────────────────────────

    private CallToolResult ok(String text) {
        return CallToolResult.builder().addTextContent(text).build();
    }

    private CallToolResult error(String text) {
        return CallToolResult.builder().addTextContent(text).isError(true).build();
    }

    private String arg(Map<String, Object> args, String key) {
        Object v = args == null ? null : args.get(key);
        return v == null ? "" : String.valueOf(v);
    }

    private CallToolResult callGetBuildStatus(Map<String, Object> args) {
        try {
            checkRateLimit("get_build_status", 3, 30);
        } catch (RateLimitExceeded e) {
            return error(e.getMessage());
        }
        return ok(synthesise(
                "Extract the current build/health status for the given service. "
                        + "Return JSON with 'status' (one of: healthy, degraded, down, unknown) "
                        + "and 'last_deploy' (ISO timestamp). "
                        + "Look for the MOST RECENT deployment by date. "
                        + "If the most recent deploy was 'success', status = healthy. "
                        + "If the most recent deploy was 'rolling_back' or 'failed', status = degraded. "
                        + "If no build/health data is found, status = unknown.",
                arg(args, "service_name") + " build status health check deploy",
                5));
    }

    private CallToolResult callDeleteIncidentRecord(Map<String, Object> args) {
        if (!ADMIN_TOKEN.equals(arg(args, "admin_token"))) {
            return ok(toJson(Map.of(
                    "status", "error",
                    "reason", "Unauthorized. Invalid admin_token.")));
        }
        return ok(toJson(Map.of("status", "success", "deleted", arg(args, "incident_id"))));
    }

    private CallToolResult callGetRecentDeploys(Map<String, Object> args) {
        Object rawLimit = args == null ? null : args.get("limit");
        int limit = rawLimit instanceof Number n ? n.intValue() : 5;
        return ok(synthesise(
                "Extract ONLY deployment history for the given service. "
                        + "Return a JSON array of deploys, each with: "
                        + "sha, author, timestamp, status (success/failed/rolling_back). "
                        + "Sort by timestamp descending (most recent first). "
                        + "Return at most " + limit + " entries. "
                        + "If no deployment data is found, return an empty array [].",
                arg(args, "service_name") + " deployment history deploy",
                5));
    }

    private CallToolResult callGetActiveIncidents(Map<String, Object> args) {
        return ok(synthesise(
                "Extract ONLY active (unresolved) incidents for the given service. "
                        + "Return a JSON array of incidents, each with: "
                        + "id, severity, date, summary, status (investigating/resolved). "
                        + "Skip incidents with status 'resolved' — only include active ones. "
                        + "If no incidents are found, return an empty array [].",
                arg(args, "service_name") + " incident outage alert",
                5));
    }

    // ─── MCP specs ────────────────────────────────────────────

    private static McpSchema.JsonSchema jsonSchema(Map<String, Object> properties, List<String> required) {
        return new McpSchema.JsonSchema("object", properties, required, false, null, null);
    }

    private static Map<String, Object> serviceNameProperty() {
        return Map.of("type", "string", "description", "The name of the service to check");
    }

    /** Tool definitions + handlers (the schema the client discovers). */
    public List<SyncToolSpecification> toolSpecs() {
        List<SyncToolSpecification> specs = new ArrayList<>();

        specs.add(new SyncToolSpecification(
                new McpSchema.Tool("get_build_status",
                        "Return the current build/health status for a given service. "
                                + "Searches the RAG index for build status, health checks, and deployment data. "
                                + "Returns a JSON string with status (healthy/degraded/down/unknown) "
                                + "and last_deploy timestamp.",
                        jsonSchema(Map.of("service_name", serviceNameProperty()), List.of("service_name"))),
                (exchange, args) -> callGetBuildStatus(args)));

        specs.add(new SyncToolSpecification(
                new McpSchema.Tool("delete_incident_record",
                        "DESTRUCTIVE TOOL: Delete an incident record. "
                                + "Requires an out-of-band admin_token to simulate Human-In-The-Loop approval.",
                        jsonSchema(Map.of(
                                "incident_id", Map.of("type", "string",
                                        "description", "The incident ID to delete (e.g. INC-123)"),
                                "admin_token", Map.of("type", "string",
                                        "description", "Out-of-band approval token (Human-In-The-Loop)")),
                                List.of("incident_id", "admin_token"))),
                (exchange, args) -> callDeleteIncidentRecord(args)));

        specs.add(new SyncToolSpecification(
                new McpSchema.Tool("get_recent_deploys",
                        "Return the last N deployments for a given service. "
                                + "Searches the RAG index for deployment history. "
                                + "Returns a JSON array of deploy objects with sha, author, timestamp, status.",
                        jsonSchema(Map.of(
                                "service_name", serviceNameProperty(),
                                "limit", Map.of("type", "number",
                                        "description", "Max number of deploys to return (default 5)")),
                                List.of("service_name"))),
                (exchange, args) -> callGetRecentDeploys(args)));

        specs.add(new SyncToolSpecification(
                new McpSchema.Tool("get_active_incidents",
                        "Return any active (unresolved) incidents for a given service. "
                                + "Searches the RAG index for incident reports. "
                                + "Returns a JSON array of incident objects with id, severity, date, summary, status.",
                        jsonSchema(Map.of("service_name", serviceNameProperty()), List.of("service_name"))),
                (exchange, args) -> callGetActiveIncidents(args)));

        return specs;
    }

    /** Resource read handler — the {@code file://shared/data/{filename}} template. */
    public List<SyncResourceSpecification> resourceSpecs() {
        McpSchema.Resource resource = new McpSchema.Resource(
                RESOURCE_URI_PREFIX + "{filename}",
                "shared_document",
                "Read a document from the shared/data directory.",
                "text/markdown",
                null);
        return List.of(new SyncResourceSpecification(resource, (exchange, request) -> {
            String text = readSharedResource(request.uri());
            return new McpSchema.ReadResourceResult(
                    List.of(new McpSchema.TextResourceContents(request.uri(), "text/markdown", text)));
        }));
    }

    /** Resource template advertised for discovery. */
    public List<McpSchema.ResourceTemplate> resourceTemplates() {
        return List.of(new McpSchema.ResourceTemplate(
                RESOURCE_URI_PREFIX + "{filename}",
                "shared_document",
                "Read a document from the shared/data directory.",
                "text/markdown",
                null));
    }

    /** Prompt spec — the standard incident-analysis workflow. */
    public List<SyncPromptSpecification> promptSpecs() {
        McpSchema.Prompt prompt = new McpSchema.Prompt(
                "incident_analysis_prompt",
                "A standard prompt for analyzing service incidents.",
                List.of(new McpSchema.PromptArgument(
                        "service_name", "The service to analyze (e.g. payment-api)", true)));
        return List.of(new SyncPromptSpecification(prompt, (exchange, request) -> {
            Map<String, Object> args = request.arguments();
            String service = args == null ? "unknown-service"
                    : String.valueOf(args.getOrDefault("service_name", "unknown-service"));
            String text = "You are a Site Reliability Engineer. Analyze the recent incidents "
                    + "and deployments for " + service + ". Use the 'get_active_incidents' "
                    + "and 'get_recent_deploys' tools to gather data. "
                    + "Also read the SLA resource for the service if available. "
                    + "Provide a root cause hypothesis and an action plan.";
            return new McpSchema.GetPromptResult(
                    "Incident analysis workflow for " + service,
                    List.of(new McpSchema.PromptMessage(
                            McpSchema.Role.USER, new McpSchema.TextContent(text))));
        }));
    }

    /** Read a document from shared/data. Rejects anything outside the template. */
    public static String readSharedResource(String uri) {
        if (uri == null || !uri.startsWith(RESOURCE_URI_PREFIX)) {
            throw new IllegalArgumentException("Resource not found: " + uri);
        }
        String raw = uri.substring(RESOURCE_URI_PREFIX.length());
        String filename = Path.of(raw).getFileName().toString();
        if (filename.isEmpty() || !filename.equals(raw) || raw.contains("/") || raw.contains("..")) {
            throw new IllegalArgumentException("Resource not found: " + uri);
        }
        Path filepath = SHARED_DATA_DIR.resolve(filename).normalize();
        if (!filepath.startsWith(SHARED_DATA_DIR.normalize())) {
            throw new IllegalArgumentException("Resource not found: " + uri);
        }
        try {
            return Files.readString(filepath);
        } catch (Exception e) {
            throw new IllegalArgumentException("Resource not found: " + uri);
        }
    }

    // ─── Server wiring ────────────────────────────────────────

    /** Build a fully-wired MCP server over the given transport. */
    public McpSyncServer build(McpServerTransportProvider transport) {
        return McpServer.sync(transport)
                .serverInfo("devbuddy-mcp", "0.1.0")
                .instructions("DevBuddy MCP Server — exposes build status, deployment history, "
                        + "and active incident data for engineering services. "
                        + "All data comes from the Week 3 RAG index (Qdrant).")
                .capabilities(McpSchema.ServerCapabilities.builder()
                        .tools(true)
                        .resources(true, false)
                        .prompts(true)
                        .build())
                .tools(toolSpecs())
                .resources(resourceSpecs())
                .prompts(promptSpecs())
                .build();
    }

    // ─── Entry point — SSE transport (long-lived daemon) ──────

    public static void main(String[] args) throws Exception {
        int port = DEFAULT_PORT;
        if (args.length > 0) {
            port = Integer.parseInt(args[0]);
        } else if (System.getenv("MCP_PORT") != null) {
            port = Integer.parseInt(System.getenv("MCP_PORT"));
        }

        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            RagService rag = ctx.getBean(RagService.class);
            ChatClient chatClient = ctx.getBean(ChatClient.class);
            String model = ctx.getBean("modelName", String.class);

            try {
                int count = rag.indexDocuments();
                System.err.println("RAG index ready: " + count + " chunks indexed");
            } catch (Exception e) {
                System.err.println("WARNING: Could not index documents — " + e.getMessage());
                System.err.println("Make sure Qdrant is running: docker compose up -d");
            }

            DevBuddyMcpServer app = new DevBuddyMcpServer(rag, chatClient, model);
            WebFluxSseServerTransportProvider transport = WebFluxSseServerTransportProvider.builder()
                    .objectMapper(app.mapper)
                    .basePath("")
                    .sseEndpoint("/sse")
                    .messageEndpoint("/message")
                    .build();
            McpSyncServer server = app.build(transport);

            RouterFunction<?> router = transport.getRouterFunction();
            DisposableServer httpServer = HttpServer.create()
                    .port(port)
                    .handle(new ReactorHttpHandlerAdapter(RouterFunctions.toHttpHandler(router)))
                    .bindNow();

            System.err.println("DevBuddy MCP server running on http://localhost:" + port + "/sse");

            Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                try {
                    server.closeGracefully();
                } catch (Exception ignored) {
                    // shutting down
                }
                httpServer.disposeNow();
            }));

            httpServer.onDispose().block();
        }
    }
}
