package devbuddy;

import devbuddy.tools.ToolData;
import devbuddy.tools.ToolEngine;
import devbuddy.tools.ToolJson;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Map;
import java.util.function.Function;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Week 4 — deterministic app-layer tests (no LLM, no Spring context).
 *
 * <p>Run: {@code mvn test -Dtest=ToolEngineTest}</p>
 */
class ToolEngineTest {

    private static Map<String, Object> call(String name, Map<String, Object> args) {
        return Map.of("name", name, "args", args == null ? Map.of() : args);
    }

    @Test
    @DisplayName("raw build_status returns a healthy status for a known service")
    void buildStatusKnownService() {
        Map<String, Object> parsed = ToolJson.parse(ToolData.buildStatus("auth-service"));
        assertEquals("healthy", parsed.get("status"));
        assertTrue(parsed.containsKey("last_deploy"));
    }

    @Test
    @DisplayName("raw build_status returns structured unknown for a bad service")
    void buildStatusUnknownService() {
        Map<String, Object> parsed = ToolJson.parse(ToolData.buildStatus("ghost"));
        assertEquals("unknown", parsed.get("status"));
        assertTrue(parsed.containsKey("error"));
    }

    @Test
    @DisplayName("executeToolSafely runs a valid call successfully")
    void executeKnownTool() {
        String result = ToolEngine.executeToolSafely(call("get_build_status",
                Map.of("service_name", "auth-service")));
        assertEquals("healthy", ToolJson.parse(result).get("status"));
    }

    @Test
    @DisplayName("the registry denies an unknown tool and lists what is available")
    void denyUnknownTool() {
        String result = ToolEngine.executeToolSafely(call("delete_production_db", Map.of()));
        Map<String, Object> parsed = ToolJson.parse(result);
        assertTrue(parsed.get("error").toString().contains("delete_production_db"));
        assertNotNull(parsed.get("available_tools"));
    }

    @Test
    @DisplayName("flaky fails N times then succeeds — per-instance counter")
    void flakyThenSucceeds() {
        Function<Map<String, Object>, String> fn =
                ToolEngine.flaky(ToolEngine.RAW_TOOLS.get("get_build_status"), 2);
        for (int i = 0; i < 2; i++) {
            try {
                fn.apply(Map.of("service_name", "auth-service"));
                throw new AssertionError("expected a failure on call " + (i + 1));
            } catch (RuntimeException expected) {
                // expected
            }
        }
        Map<String, Object> ok = ToolJson.parse(fn.apply(Map.of("service_name", "auth-service")));
        assertEquals("healthy", ok.get("status"));
    }

    @Test
    @DisplayName("persistent failure returns a structured error after retries burn out")
    void exhaustedRetriesReturnStructuredError() {
        Function<Map<String, Object>, String> alwaysFail =
                ToolEngine.flaky(ToolEngine.RAW_TOOLS.get("get_build_status"), 99);
        Map<String, Function<Map<String, Object>, String>> registry = Map.of(
                "get_build_status", alwaysFail);

        String result = ToolEngine.executeToolSafely(
                call("get_build_status", Map.of("service_name", "payment-api")),
                1, registry, false, 0);

        Map<String, Object> parsed = ToolJson.parse(result);
        assertEquals("failed", parsed.get("status"));
        assertEquals(2, parsed.get("attempts")); // 1 initial + 1 retry
        assertTrue(parsed.containsKey("error"));
    }
}
