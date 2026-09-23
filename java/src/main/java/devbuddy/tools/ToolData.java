package devbuddy.tools;

import java.util.List;
import java.util.Map;

/**
 * Week 4 — tool data + raw functions (mirrors python/node src.tools).
 *
 * <p>Raw functions own the data and return JSON strings. Tool wrappers
 * (Spring {@code ToolCallback}s in {@link ToolCatalog}) and demos build on
 * these — nothing is ever duplicated.</p>
 */
public final class ToolData {

    public static final Map<String, Map<String, Object>> BUILD_STATUSES = Map.of(
            "auth-service", Map.of("status", "healthy", "last_deploy", "2026-06-28T08:15:00Z"),
            "payment-api", Map.of(
                    "status", "degraded",
                    "last_deploy", "2026-06-28T06:45:00Z",
                    "failing_since", "2026-06-28T07:30:00Z"),
            "inventory-service", Map.of("status", "unknown", "last_deploy", "2026-06-20T11:00:00Z"));

    public static final Map<String, List<Map<String, Object>>> DEPLOYS = Map.of(
            "auth-service", List.of(
                    Map.of("sha", "abc123def456", "author", "tabish", "timestamp", "2026-06-28T08:15:00Z", "status", "success"),
                    Map.of("sha", "789ghi012jkl", "author", "alex", "timestamp", "2026-06-27T14:30:00Z", "status", "success")),
            "payment-api", List.of(
                    Map.of("sha", "def789ghi012", "author", "maria", "timestamp", "2026-06-28T06:45:00Z", "status", "success"),
                    Map.of("sha", "jkl345mno678", "author", "maria", "timestamp", "2026-06-27T22:00:00Z", "status", "rolling_back"),
                    Map.of("sha", "pqr901stu234", "author", "jordan", "timestamp", "2026-06-27T20:15:00Z", "status", "failed")),
            "inventory-service", List.of());

    public static final Map<String, List<Map<String, Object>>> INCIDENTS = Map.of(
            "payment-api", List.of(Map.of(
                    "id", "INC-842", "severity", "Sev1",
                    "summary", "payment-api latency spike. 15% of requests affected. Error code 408.",
                    "status", "investigating")),
            "auth-service", List.of(),
            "inventory-service", List.of(Map.of(
                    "id", "INC-901", "severity", "Sev3",
                    "summary", "inventory-service data inconsistency between primary and replica.",
                    "status", "investigating")));

    private ToolData() {
    }

    /** Current build/health status of a service as a JSON string. */
    public static String buildStatus(String serviceName) {
        Map<String, Object> data = BUILD_STATUSES.get(serviceName);
        if (data == null) {
            return ToolJson.toJson(Map.of(
                    "status", "unknown",
                    "error", "No data for service '" + serviceName + "'"));
        }
        return ToolJson.toJson(data);
    }

    /** Last N deployments of a service as a JSON string. */
    public static String recentDeploys(String serviceName, int limit) {
        List<Map<String, Object>> deploys = DEPLOYS.getOrDefault(serviceName, List.of());
        return ToolJson.toJson(deploys.size() > limit ? deploys.subList(0, limit) : deploys);
    }

    /** Active (unresolved) incidents of a service as a JSON string. */
    public static String activeIncidents(String serviceName) {
        return ToolJson.toJson(INCIDENTS.getOrDefault(serviceName, List.of()));
    }
}
