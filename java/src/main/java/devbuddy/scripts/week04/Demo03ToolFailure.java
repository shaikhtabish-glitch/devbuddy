package devbuddy.scripts.week04;

import devbuddy.tools.ToolEngine;
import devbuddy.tools.ToolJson;

import java.util.HashMap;
import java.util.Map;
import java.util.function.Function;

/**
 * Week 4 — Demo 3: Tool Failure — retry & denial live in the app layer.
 *
 * <p>THE POINT: retry, denial, and error format are CODE decisions —
 * deterministic, testable, auditable. The model only ever sees the final
 * result: success or a structured error. Never trust the raw tool request.</p>
 *
 * <p>Act 1 — retry drill via {@code flaky}. Act 2 — the registry guardrail
 * denies tools the model was never given. Fully deterministic (no LLM).</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week04.Demo03ToolFailure}</p>
 */
public class Demo03ToolFailure {

    public static void main(String[] args) {
        System.out.println("=".repeat(70));
        System.out.println("  Demo 3: Tool Failure — Retry & Denial Live in the App Layer");
        System.out.println("=".repeat(70));
        System.out.println();

        Map<String, Object> toolCall = call("get_build_status", "payment-api");

        // ── Act 1: retry in the app layer ─────────────────────
        System.out.println("  ── Act 1: Retry in the app layer ───────────────────────────");
        System.out.println();
        String[] labels = {"normal", "transient", "exhausted"};
        int[] failNs = {0, 1, 99};
        for (int s = 0; s < labels.length; s++) {
            System.out.println("  ── scenario: " + labels[s] + " ──");
            Function<Map<String, Object>, String> raw =
                    ToolEngine.RAW_TOOLS.get("get_build_status");
            Map<String, Function<Map<String, Object>, String>> registry = Map.of(
                    "get_build_status", ToolEngine.flaky(raw, failNs[s]));
            String result = ToolEngine.executeToolSafely(toolCall, 2, registry, true, 0);
            Map<String, Object> parsed = ToolJson.parse(result);
            if (parsed.containsKey("error")) {
                System.out.println("     ❌ structured error after " + parsed.get("attempts") + " attempts");
            } else {
                System.out.println("     ✅ returned: " + shortJson(result));
            }
            System.out.println();
        }
        System.out.println("  Retries ran inside ToolEngine.executeToolSafely() — your code,");
        System.out.println("  not the model's. The model never saw the failures.");
        System.out.println();

        // ── Act 2: the guardrail — never trust the raw request ─
        System.out.println("  ── Act 2: The guardrail — never trust the raw request ───────");
        System.out.println();
        String denied = ToolEngine.executeToolSafely(call("delete_production_db", null));
        System.out.println("  Request: delete_production_db({})");
        System.out.println("  Response: " + denied);
        System.out.println("  → DENIED by the registry. The model can never reach code it was");
        System.out.println("    not given — that is what the whitelist is for.");
        System.out.println();
        String unknown = ToolEngine.executeToolSafely(call("get_build_status", "ghost-service"));
        System.out.println("  Request: get_build_status(ghost-service)");
        System.out.println("  Response: " + unknown);
        System.out.println("  → A valid tool with bad args returns structured 'no data'. No crash.");
        System.out.println();

        System.out.println("=".repeat(70));
        System.out.println("  THE MESSAGE: retry logic, denial, and error format are CODE");
        System.out.println("  decisions — deterministic, testable, auditable. The model's");
        System.out.println("  recovery is unreliable by design; your application layer is");
        System.out.println("  what ships. Never trust the raw tool request.");
        System.out.println();
        System.out.println("  YOUR TURN:");
        System.out.println("    • Change the retry budget in Act 1 and watch attempts move.");
        System.out.println("    • Feed the structured error to a model (ToolLoop) and watch");
        System.out.println("      it degrade gracefully instead of inventing data.");
        System.out.println("=".repeat(70));
    }

    private static Map<String, Object> call(String name, String service) {
        Map<String, Object> args = service == null ? new HashMap<>() : Map.of("service_name", service);
        return Map.of("name", name, "args", args);
    }

    private static String shortJson(String json) {
        return json.length() > 110 ? json.substring(0, 110) + "…" : json;
    }
}
