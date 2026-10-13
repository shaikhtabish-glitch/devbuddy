package devbuddy.scripts.week05;

import io.modelcontextprotocol.client.McpSyncClient;
import io.modelcontextprotocol.spec.McpSchema;

import java.util.Map;

/**
 * Week 5 — Demo 3: Protocol Errors & Resilience.
 *
 * <p>THE POINT: MCP connections fail in predictable ways. Since you now
 * request Context over a network, you must handle network errors, missing
 * resources, and missing tools. These are operational patterns, not bugs.</p>
 *
 * <p>Prerequisites: MCP server running on port 8002.</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week05.Demo03BreakIt}</p>
 */
public class Demo03BreakIt {

    private static void printError(Exception e) {
        String msg = e.getMessage() == null ? e.toString() : e.getMessage();
        System.out.println("  [OUTPUT] ← ❌ [" + e.getClass().getSimpleName() + "] "
                + msg.substring(0, Math.min(120, msg.length())));
        System.out.println();
    }

    public static void main(String[] args) {
        DemoSupport.header("Demo 3: Protocol Errors & Resilience");
        System.out.println();
        System.out.println("  When you shift to an ecosystem model, failure handling moves");
        System.out.println("  from Try/Catch blocks to Application Layer Routing.");
        System.out.println();

        // ── Act 1: Resource Not Found ──────────────────────────────
        System.out.println("  ── Act 1: Requesting a missing Resource ──────────────────");
        System.out.println("  Client asks for a file that isn't exposed or doesn't exist.");
        System.out.println();
        String targetUri = "file:///etc/passwd";
        System.out.println("  [INPUT]  → client.readResource('" + targetUri + "')");
        McpSyncClient c1 = null;
        try {
            c1 = DemoSupport.connect();
            c1.readResource(new McpSchema.ReadResourceRequest(targetUri));
            System.out.println("  [OUTPUT] ← ❓ Unexpected success");
            System.out.println();
        } catch (Exception e) {
            printError(e);
        } finally {
            if (c1 != null) c1.closeGracefully();
        }
        System.out.println("  KEY INSIGHT: The server explicitly rejected this. Path traversal");
        System.out.println("  is blocked by the protocol mapping.");
        System.out.println();
        DemoSupport.pause("  ⏸  Press Enter to continue… ");

        // ── Act 2: Tool Not Found ──────────────────────────────────
        System.out.println("  ── Act 2: Requesting a missing Tool ──────────────────────");
        System.out.println("  Client attempts to execute a legacy tool name.");
        System.out.println();
        String toolName = "get_buildstatus"; // intentionally misspelled
        System.out.println("  [INPUT]  → client.callTool({ name: '" + toolName
                + "', arguments: {service_name: 'auth-service'} })");
        McpSyncClient c2 = null;
        try {
            c2 = DemoSupport.connect();
            c2.callTool(new McpSchema.CallToolRequest(toolName, Map.of("service_name", "auth-service")));
            System.out.println("  [OUTPUT] ← ❓ Unexpected success");
            System.out.println();
        } catch (Exception e) {
            printError(e);
        } finally {
            if (c2 != null) c2.closeGracefully();
        }
        System.out.println("  KEY INSIGHT: Unknown tool errors come from the SERVER.");
        System.out.println("  The client must handle this and re-plan using listTools().");
        System.out.println();
        DemoSupport.pause("  ⏸  Press Enter to continue… ");

        // ── Act 3: Connection Error ────────────────────────────────
        System.out.println("  ── Act 3: Server Offline ─────────────────────────────────");
        System.out.println("  Client attempts to connect to a server that isn't running.");
        System.out.println();
        String badUrl = "http://127.0.0.1:9999";
        System.out.println("  [INPUT]  → connecting to '" + badUrl + "'");
        McpSyncClient c3 = null;
        try {
            c3 = DemoSupport.connect(badUrl);
            System.out.println("  [OUTPUT] ← ❓ Unexpected success");
            System.out.println();
        } catch (Exception e) {
            printError(e);
        } finally {
            if (c3 != null) c3.closeGracefully();
        }
        System.out.println("  KEY INSIGHT: Connection errors happen at the transport layer,");
        System.out.println("  before MCP even initializes. Your client needs retry logic with");
        System.out.println("  exponential backoff.");
        System.out.println();

        System.out.println(DemoSupport.BORDER);
        System.out.println("  THE MESSAGE: The protocol enforces strict contracts. Your AI orchestrator");
        System.out.println("  must handle these rejections gracefully, dynamically re-querying the");
        System.out.println("  context server when resources or tools shift.");
        System.out.println(DemoSupport.BORDER);
    }
}
