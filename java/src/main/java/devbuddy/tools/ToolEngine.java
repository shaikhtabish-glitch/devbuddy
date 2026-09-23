package devbuddy.tools;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Function;

/**
 * Week 4 — the deterministic application layer (mirrors python/node).
 *
 * <p>{@code executeToolSafely} is the whitelist + retry + structured-error
 * guardrail. The model never runs a tool — it returns {@code {name, args}},
 * and this class decides whether that request becomes an action. {@code flaky}
 * is a deterministic per-instance failure injector for demos/tests.</p>
 */
public final class ToolEngine {

    public static final int MAX_TOOL_TURNS = 6;

    private ToolEngine() {
    }

    /** Default registry: tool name → raw function ({name,args} → JSON string). */
    public static final Map<String, Function<Map<String, Object>, String>> RAW_TOOLS = Map.of(
            "get_build_status", args -> ToolData.buildStatus(str(args.get("service_name"))),
            "get_recent_deploys", args -> ToolData.recentDeploys(str(args.get("service_name")),
                    args.get("limit") == null ? 5 : ((Number) args.get("limit")).intValue()),
            "get_active_incidents", args -> ToolData.activeIncidents(str(args.get("service_name"))));

    private static String str(Object o) {
        return o == null ? "" : String.valueOf(o);
    }

    /**
     * Execute a tool call with retry + deny, all in the application layer.
     *
     * @param call         {@code {name, args}}
     * @param maxRetries   retries after the initial attempt
     * @param registry     name → function (defaults to {@link #RAW_TOOLS})
     * @param verbose      print failed attempts as they retry
     * @param retryDelayMs backoff between attempts (0 in tests)
     * @return tool result, or a structured error ({@code status: failed})
     */
    public static String executeToolSafely(Map<String, Object> call, int maxRetries,
                                           Map<String, Function<Map<String, Object>, String>> registry,
                                           boolean verbose, long retryDelayMs) {
        Map<String, Function<Map<String, Object>, String>> reg =
                registry == null ? RAW_TOOLS : registry;
        String toolName = str(call.get("name"));
        Function<Map<String, Object>, String> toolFn = reg.get(toolName);

        if (toolFn == null) {
            return ToolJson.toJson(Map.of(
                    "error", "Unknown tool: '" + toolName + "'",
                    "available_tools", new ArrayList<>(reg.keySet())));
        }

        @SuppressWarnings("unchecked")
        Map<String, Object> args = (Map<String, Object>) call.getOrDefault("args", Map.of());
        String lastError = null;
        for (int attempt = 1; attempt <= maxRetries + 1; attempt++) {
            try {
                return toolFn.apply(args);
            } catch (Exception e) {
                lastError = e.getMessage() == null ? e.toString() : e.getMessage();
                if (attempt <= maxRetries) {
                    if (verbose) {
                        System.out.printf("       ⚠️  attempt %d failed (%s) — retrying…%n", attempt, lastError);
                    }
                    try {
                        Thread.sleep(retryDelayMs);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        }

        Map<String, Object> error = new LinkedHashMap<>();
        error.put("error", lastError);
        error.put("tool", toolName);
        error.put("status", "failed");
        error.put("attempts", maxRetries + 1);
        error.put("hint", "The tool is temporarily unavailable. Try a different approach.");
        return ToolJson.toJson(error);
    }

    /** Convenience: default registry, no retry print, no backoff. */
    public static String executeToolSafely(Map<String, Object> call) {
        return executeToolSafely(call, 2, null, false, 1000);
    }

    /**
     * Deterministic failure injection: the first {@code failFirstN} calls throw,
     * later calls succeed. Each wrapper owns its own counter.
     */
    public static Function<Map<String, Object>, String> flaky(
            Function<Map<String, Object>, String> fn, int failFirstN) {
        AtomicInteger calls = new AtomicInteger();
        return args -> {
            int made = calls.incrementAndGet();
            if (made <= failFirstN) {
                throw new RuntimeException("Simulated failure " + made + "/" + failFirstN);
            }
            return fn.apply(args);
        };
    }
}
