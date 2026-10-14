package devbuddy.agent;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Registry — the single source of truth for what the agent can do.
 *
 * <p>One source of truth, four surfaces (mirror of Python's NODE_REGISTRY
 * and Node's NODE_REGISTRY):</p>
 * <ol>
 *   <li>the router's step list ({@link #routerCatalog()})</li>
 *   <li>the graph's route map ({@link #PLAN_ROUTE_MAP})</li>
 *   <li>the guard's per-category requirements ({@link #REQUIREMENTS})</li>
 *   <li>the refusal message ({@link #refusalList()})</li>
 * </ol>
 *
 * <p>All static — the registry is data, the nodes are functions (see
 * {@link Nodes}), and the graph wires them together (see {@link Graph}).</p>
 */
public final class Registry {

    private Registry() {
    }

    /** One registered step: its graph node id, the state field it fills, the
     *  description the router sees. */
    public record NodeSpec(String nodeId, String dataField, String desc) {
    }

    public static final Map<String, NodeSpec> NODE_REGISTRY = new LinkedHashMap<>();

    static {
        NODE_REGISTRY.put("retrieve", new NodeSpec(
                "retrieve_context", "context",
                "Search internal documentation for the query (no service needed)"));
        NODE_REGISTRY.put("check_build", new NodeSpec(
                "check_build", "build_status",
                "Get CI/CD build/health status for the service"));
        NODE_REGISTRY.put("check_deploys", new NodeSpec(
                "check_deploys", "deploys",
                "Get recent deployment history for the service"));
        NODE_REGISTRY.put("check_incidents", new NodeSpec(
                "check_incidents", "incidents",
                "Get active (unresolved) incidents for the service"));
    }

    /** data field → registry step that fills it. */
    public static final Map<String, String> FIELD_TO_STEP = new LinkedHashMap<>();

    static {
        NODE_REGISTRY.forEach((name, spec) -> FIELD_TO_STEP.put(spec.dataField(), name));
    }

    /** Query category → state fields that MUST be present before a report. */
    public static final Map<String, List<String>> REQUIREMENTS = Map.of(
            "full", List.of("build_status", "deploys", "incidents"),
            "readiness", List.of("build_status", "deploys"),
            "health", List.of("build_status"),
            "deploys", List.of("deploys"),
            "incidents", List.of("incidents"),
            "docs", List.of("context"),
            "general", List.of(),
            "action", List.of() // imperative — refused before validate ever runs
    );

    /**
     * Imperative operational actions — refused deterministically, before any
     * LLM call. An agent with no deploy tool must not depend on a lucky
     * prompt to refuse a deploy.
     */
    public static final Pattern IMPERATIVE_ACTIONS = Pattern.compile(
            "^\\s*(deploy|roll\\s?back|rollback|restart|scale|delete|kill|shutdown|wipe)\\b");

    /**
     * Deterministic query categories — code, not prompt.
     *
     * <p>Returns ALL matched categories joined with {@code '+'} (multi-intent
     * queries get the UNION of steps and requirements), so a query asking
     * about deployments AND incidents never has a legitimate step rejected
     * as out-of-scope.</p>
     */
    public static String classifyQuery(String query) {
        String q = query.toLowerCase();
        if (IMPERATIVE_ACTIONS.matcher(q).find()) {
            return "action";
        }
        if (q.matches(".*(\\bfull\\b|\\beverything\\b|\\ball checks\\b|\\bend-to-end\\b).*")) {
            return "full";
        }
        List<String> cats = new ArrayList<>();
        if (q.matches(".*\\b(ready|readiness|release|assessment|ship)\\b.*")) {
            cats.add("readiness");
        }
        if (q.contains("incident") || q.contains("outage") || q.contains("alert")) {
            cats.add("incidents");
        }
        if (q.matches(".*(deployed|deployment|\\bsha\\b|version).*")) {
            cats.add("deploys");
        }
        if (q.matches(".*(healthy|health|status|\\bbuild\\b).*")) {
            cats.add("health");
        }
        // NOTE: no bare "api" — service names like "payment-api" would match
        // every query and silently force the docs category on all of them.
        if (q.matches(".*(doc|spec|endpoint|sla|\\bhow\\b|what is|why|describe|explain).*")) {
            cats.add("docs");
        }
        return cats.isEmpty() ? "general" : String.join("+", cats);
    }

    /** The router's step list — GENERATED from the registry. */
    public static String routerCatalog() {
        StringBuilder sb = new StringBuilder();
        NODE_REGISTRY.forEach((name, spec) ->
                sb.append("- ").append(name).append(": ").append(spec.desc()).append('\n'));
        sb.append("- report: every field NEEDED for this query has been collected\n");
        sb.append("- done: the task is complete or cannot proceed");
        return sb.toString();
    }

    /**
     * The graph's route map — GENERATED from the registry too.
     *
     * <p>{@code report}/{@code done} from the planner = "wrap up" → the
     * GUARD decides (report or blocked answer). Only {@code stop}
     * (budget exhausted) ends the run.</p>
     */
    public static final Map<String, String> PLAN_ROUTE_MAP = new LinkedHashMap<>();

    static {
        NODE_REGISTRY.forEach((name, spec) -> PLAN_ROUTE_MAP.put(name, name));
        PLAN_ROUTE_MAP.put("report", "validate");
        PLAN_ROUTE_MAP.put("done", "validate");
        PLAN_ROUTE_MAP.put("validate", "validate");
        PLAN_ROUTE_MAP.put("refuse", "refuse");
        PLAN_ROUTE_MAP.put("stop", Graph.END);
    }

    /** Steps the model may propose for this query: every registered step
     *  whose data field is required by any matched category, plus retrieve
     *  (documentation is always allowed context). */
    public static Set<String> allowedSteps(String query) {
        Set<String> allowed = new LinkedHashSet<>();
        for (String category : queryCategories(query)) {
            for (String field : REQUIREMENTS.getOrDefault(category, List.of())) {
                String step = FIELD_TO_STEP.get(field);
                if (step != null) {
                    allowed.add(step);
                }
            }
        }
        allowed.add("retrieve");
        return allowed;
    }

    public static String[] queryCategories(String query) {
        return classifyQuery(query).split("\\+");
    }

    /** Required data fields for this query, de-duplicated, in order. */
    public static List<String> requiredFields(String query) {
        List<String> needed = new ArrayList<>();
        for (String category : queryCategories(query)) {
            for (String field : REQUIREMENTS.getOrDefault(category, List.of())) {
                if (!needed.contains(field)) {
                    needed.add(field);
                }
            }
        }
        return needed;
    }

    /** Required fields that state hasn't collected yet. */
    public static List<String> requiredMissing(AgentState state) {
        List<String> missing = new ArrayList<>();
        for (String field : requiredFields(state.query)) {
            if (!state.filled(field)) {
                missing.add(field);
            }
        }
        return missing;
    }

    /**
     * Acceptable proposal? Only if it's a real, in-scope step whose data
     * isn't collected yet AND that hasn't already failed this run — retries
     * live at the transport; the planner must never hammer a broken tool.
     */
    public static boolean stepOk(String proposal, AgentState state, Set<String> allowed) {
        if (!NODE_REGISTRY.containsKey(proposal)) {
            return proposal.equals("report") || proposal.equals("done");
        }
        if (!allowed.contains(proposal)) {
            return false;
        }
        Set<String> failed = new LinkedHashSet<>();
        for (AuditRecord m : state.messages) {
            if ("failed".equals(m.getString("status"))) {
                failed.add(m.step());
            }
        }
        NodeSpec spec = NODE_REGISTRY.get(proposal);
        if (failed.contains(spec.nodeId())) {
            return false;
        }
        return !state.filled(spec.dataField());
    }

    /** The refusal message, CONSTRUCTED from the registry — the model never
     *  invents what the agent can do. */
    public static String refusalList() {
        return String.join(", ", NODE_REGISTRY.keySet());
    }

    /** All registry + planner step names the router may ever return. */
    public static Set<String> knownDecisions() {
        Set<String> known = new LinkedHashSet<>(NODE_REGISTRY.keySet());
        known.add("report");
        known.add("done");
        return known;
    }
}