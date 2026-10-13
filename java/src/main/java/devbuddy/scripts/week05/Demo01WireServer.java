package devbuddy.scripts.week05;

import io.modelcontextprotocol.client.McpSyncClient;
import io.modelcontextprotocol.spec.McpSchema;

import java.util.Map;

/**
 * Week 5 — Demo 1: Discovering Context (Resources & Prompts).
 *
 * <p>THE POINT: connect to the MCP server and ask it for Context, not just
 * Tools. Discover the shared markdown documents (Resources) and standard
 * operational templates (Prompts) — without hardcoding either.</p>
 *
 * <p>Prerequisites: MCP server running in another terminal:</p>
 * <pre>mvn -q compile exec:java -Dexec.mainClass=devbuddy.mcp.DevBuddyMcpServer</pre>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week05.Demo01WireServer}</p>
 */
public class Demo01WireServer {

    public static void main(String[] args) {
        McpSyncClient client = null;
        try {
            client = DemoSupport.connect();

            DemoSupport.header("Demo 1: Discovering Context (Resources & Prompts)");
            System.out.println();

            // ── Step 1: Discover Resources ─────────────────────────
            System.out.println("  ── Step 1: Discover Resources ─────────────────────");
            System.out.println("  Instead of writing a custom tool to read the SLA document,");
            System.out.println("  the server exposes it as a standard Resource.");
            System.out.println();

            McpSchema.ListResourcesResult resources = client.listResources();
            McpSchema.ListResourceTemplatesResult templates = client.listResourceTemplates();
            int total = resources.resources().size() + templates.resourceTemplates().size();
            System.out.println("  Server exposes " + total + " resource(s) / template(s):");
            for (McpSchema.Resource r : resources.resources()) {
                System.out.println("    • [Static] " + r.name() + " (URI: " + r.uri() + ")");
            }
            for (McpSchema.ResourceTemplate t : templates.resourceTemplates()) {
                System.out.println("    • [Template] " + t.name() + " (URI: " + t.uriTemplate() + ")");
            }
            System.out.println();

            System.out.println("  ⏸  Let's read a resource directly via the protocol.");
            DemoSupport.pause("  ⏸  Press Enter to continue… ");

            String targetUri = "file://shared/data/inventory-service-sla.md";
            System.out.println("  Reading: " + targetUri);
            try {
                McpSchema.ReadResourceResult data = client.readResource(
                        new McpSchema.ReadResourceRequest(targetUri));
                String text = ((McpSchema.TextResourceContents) data.contents().get(0)).text();
                System.out.println("  Contents:");
                System.out.println("    " + text.strip());
            } catch (Exception e) {
                System.out.println("  ❌ Error reading resource: " + e.getMessage());
            }
            System.out.println();

            // ── Step 2: Discover Prompts ───────────────────────────
            System.out.println("  ── Step 2: Discover Prompts ───────────────────────");
            System.out.println("  The server also holds the standard playbook for incident analysis.");
            System.out.println("  The client doesn't need to hardcode the prompt.");
            System.out.println();

            McpSchema.ListPromptsResult prompts = client.listPrompts();
            System.out.println("  Server exposes " + prompts.prompts().size() + " prompt(s):");
            for (McpSchema.Prompt p : prompts.prompts()) {
                String desc = p.description() == null ? "(no description)" : p.description();
                System.out.println("    • " + p.name() + ": " + desc);
                if (p.arguments() != null && !p.arguments().isEmpty()) {
                    System.out.println("      Args: " + p.arguments().stream()
                            .map(McpSchema.PromptArgument::name).toList());
                } else {
                    System.out.println("      Args: None");
                }
            }
            System.out.println();

            System.out.println("  ⏸  Let's fetch the prompt template for 'auth-service'.");
            DemoSupport.pause("  ⏸  Press Enter to continue… ");

            try {
                McpSchema.GetPromptResult prompt = client.getPrompt(
                        new McpSchema.GetPromptRequest(
                                "incident_analysis_prompt", Map.of("service_name", "auth-service")));
                System.out.println("  Returned Prompt Message:");
                System.out.println("    " + prompt.description());
                for (McpSchema.PromptMessage msg : prompt.messages()) {
                    String text = ((McpSchema.TextContent) msg.content()).text();
                    System.out.println("    Content: " + text.substring(0, Math.min(80, text.length())) + "...");
                }
            } catch (Exception e) {
                System.out.println("  ❌ Error fetching prompt: " + e.getMessage());
            }
            System.out.println();

            System.out.println(DemoSupport.BORDER);
            System.out.println("  THE SHIFT: Your client just read a proprietary document and");
            System.out.println("  fetched an operational workflow without calling a single 'tool'.");
            System.out.println("  This is Context Engineering.");
            System.out.println(DemoSupport.BORDER);
        } catch (Exception e) {
            DemoSupport.connectionHint();
            System.err.println("  " + e.getMessage());
        } finally {
            if (client != null) {
                client.closeGracefully();
            }
        }
    }
}
