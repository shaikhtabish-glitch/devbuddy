package devbuddy;

import devbuddy.mcp.DevBuddyMcpServer;
import io.modelcontextprotocol.spec.McpSchema;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Week 5 — tests for {@link DevBuddyMcpServer}.
 *
 * <p>Exercises the tool/resource/prompt specs, the resource reader, the
 * destructive-tool guard, and the rate limiter — no LLM or Qdrant required.</p>
 */
class McpServerTest {

    private DevBuddyMcpServer newServer() {
        return new DevBuddyMcpServer(null, null, "test-model");
    }

    @Test
    void registersAllFourTools() {
        List<String> names = newServer().toolSpecs().stream()
                .map(s -> s.tool().name()).toList();
        assertTrue(names.contains("get_build_status"));
        assertTrue(names.contains("delete_incident_record"));
        assertTrue(names.contains("get_recent_deploys"));
        assertTrue(names.contains("get_active_incidents"));
        assertEquals(4, names.size());
    }

    @Test
    void exposesOneResourceTemplate() {
        var templates = newServer().resourceTemplates();
        assertEquals(1, templates.size());
        assertEquals("file://shared/data/{filename}", templates.get(0).uriTemplate());
        assertEquals(1, newServer().resourceSpecs().size());
    }

    @Test
    void definesIncidentPrompt() {
        var prompts = newServer().promptSpecs();
        assertEquals(1, prompts.size());
        assertEquals("incident_analysis_prompt", prompts.get(0).prompt().name());
    }

    @Test
    void readsSharedDocument() {
        String text = DevBuddyMcpServer.readSharedResource(
                "file://shared/data/inventory-service-sla.md");
        assertTrue(text.contains("Inventory Service"));
    }

    @Test
    void rejectsPathsOutsideSharedData() {
        assertThrows(IllegalArgumentException.class,
                () -> DevBuddyMcpServer.readSharedResource("file:///etc/passwd"));
        assertThrows(IllegalArgumentException.class,
                () -> DevBuddyMcpServer.readSharedResource("file://shared/data/../../etc/passwd"));
    }

    @Test
    void rateLimitsAfterThreeCalls() {
        DevBuddyMcpServer server = newServer();
        for (int i = 0; i < 3; i++) {
            server.checkRateLimit("test_tool", 3, 30);
        }
        assertThrows(DevBuddyMcpServer.RateLimitExceeded.class,
                () -> server.checkRateLimit("test_tool", 3, 30));
        server.resetRateLimits();
    }

    @Test
    void destructiveToolRequiresAdminToken() {
        var spec = newServer().toolSpecs().stream()
                .filter(s -> s.tool().name().equals("delete_incident_record"))
                .findFirst().orElseThrow();

        McpSchema.CallToolResult denied = spec.call().apply(null,
                Map.of("incident_id", "INC-1", "admin_token", "nope"));
        assertTrue(((McpSchema.TextContent) denied.content().get(0)).text().contains("Unauthorized"));

        McpSchema.CallToolResult allowed = spec.call().apply(null,
                Map.of("incident_id", "INC-1", "admin_token", "super-secret-approval-123"));
        String body = ((McpSchema.TextContent) allowed.content().get(0)).text();
        assertTrue(body.contains("success"));
        assertTrue(body.contains("INC-1"));
    }
}
