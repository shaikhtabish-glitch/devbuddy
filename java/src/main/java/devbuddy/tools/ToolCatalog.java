package devbuddy.tools;

import org.springframework.ai.tool.ToolCallback;
import org.springframework.ai.tool.function.FunctionToolCallback;

import java.util.ArrayList;
import java.util.List;

/**
 * Week 4 — Spring AI {@link ToolCallback} wrappers over {@link ToolData}.
 *
 * <p>The callback is the schema the model sees: name + description +
 * parameter type. The description is what teaches the model to route
 * (see demo-02 for the vague-vs-precise lever).</p>
 */
public final class ToolCatalog {

    private ToolCatalog() {
    }

    public record ServiceArgs(String service_name) {
    }

    public record DeploysArgs(String service_name, Integer limit) {
    }

    /**
     * Build the three callbacks. Every executed call is appended to
     * {@code recorded} as {@code name(args) => result[:80]} — this is the
     * audit trail the demos print.
     */
    public static List<ToolCallback> callbacks(List<String> recorded) {
        List<ToolCallback> out = new ArrayList<>();

        out.add(FunctionToolCallback.builder("get_build_status", (ServiceArgs a) -> {
            String result = ToolData.buildStatus(a.service_name());
            recorded.add("get_build_status(" + a.service_name() + ") => " + shortJson(result));
            return result;
        }).description(
                "Return the current build/health status for a service: 'healthy', 'degraded', " +
                        "'down', or 'unknown', plus last deploy time. Use for questions like 'is X healthy?'")
                .inputType(ServiceArgs.class).build());

        out.add(FunctionToolCallback.builder("get_recent_deploys", (DeploysArgs a) -> {
            int limit = a.limit() == null ? 5 : a.limit();
            String result = ToolData.recentDeploys(a.service_name(), limit);
            recorded.add("get_recent_deploys(" + a.service_name() + ", limit=" + limit + ") => " + shortJson(result));
            return result;
        }).description(
                "Return the last N deployments for a service (sha, author, timestamp, status). " +
                        "Use for questions like 'what was deployed recently for X?'")
                .inputType(DeploysArgs.class).build());

        out.add(FunctionToolCallback.builder("get_active_incidents", (ServiceArgs a) -> {
            String result = ToolData.activeIncidents(a.service_name());
            recorded.add("get_active_incidents(" + a.service_name() + ") => " + shortJson(result));
            return result;
        }).description(
                "Return any active (unresolved) incidents for a given service. " +
                        "Use for questions like 'are there active incidents for X?'")
                .inputType(ServiceArgs.class).build());

        return out;
    }

    /** Vague-description variant (demo-02 Part B: the routing lever). */
    public static List<ToolCallback> callbacksVague(List<String> recorded) {
        return List.of(
                FunctionToolCallback.builder("get_build_status", (ServiceArgs a) -> {
                    String result = ToolData.buildStatus(a.service_name());
                    recorded.add("get_build_status(" + a.service_name() + ") => " + shortJson(result));
                    return result;
                }).description("Get service information.").inputType(ServiceArgs.class).build(),
                FunctionToolCallback.builder("get_recent_deploys", (DeploysArgs a) -> {
                    int limit = a.limit() == null ? 5 : a.limit();
                    String result = ToolData.recentDeploys(a.service_name(), limit);
                    recorded.add("get_recent_deploys(" + a.service_name() + ", limit=" + limit + ") => " + shortJson(result));
                    return result;
                }).description("Get records.").inputType(DeploysArgs.class).build());
    }

    private static String shortJson(String json) {
        return json.length() > 80 ? json.substring(0, 80) + "…" : json;
    }
}
