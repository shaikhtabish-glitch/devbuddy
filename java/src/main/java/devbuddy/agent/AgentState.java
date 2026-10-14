package devbuddy.agent;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Week 6 — agent state, carried across all steps.
 *
 * <p>The Java sibling of Python's {@code AgentState} TypedDict and Node's
 * {@code initState()}. Deliberate scope choice (docs → Scope: languages):
 * data fields stay raw JSON <em>strings</em> — no per-field contracts — so the
 * guard's emptiness checks read the same as Python's.</p>
 *
 * <p>Every field starts &quot;empty&quot; ({@code ""} / {@code null}): empty
 * means <b>not checked yet</b>, which is exactly what C2 exploits and the
 * validity guard rejects.</p>
 */
public class AgentState {

    public String query;
    /** "" = not extracted yet */
    public String serviceName = "";
    /** "" = not retrieved yet */
    public String context = "";
    /** "" = not checked yet (JSON when set) */
    public String buildStatus = "";
    /** "" = not checked yet (JSON array when set) */
    public String deploys = "";
    /** "" = not checked yet (JSON array when set) */
    public String incidents = "";
    /** null = not generated yet */
    public AgentAnswer report;
    /** planner's accepted decision */
    public String nextStep = "";
    public int steps;
    public double cost;
    /** "" = no failure so far */
    public String error = "";
    /** audit trail — recorded, never reconstructed */
    public final List<AuditRecord> messages = new ArrayList<>();

    public AgentState(String query) {
        this.query = query;
    }

    /**
     * Append one event to the audit trail. Every node records itself and
     * carries the COST DELTA since the previous event — per-step cost is
     * traceable, not just the run total.
     */
    public void record(String step, Map<String, Object> detail) {
        double prevTotal = messages.stream().mapToDouble(m -> m.cost()).sum();
        Map<String, Object> d = detail == null ? Map.of() : detail;
        d.put("cost", Math.round((cost - prevTotal) * 1e6) / 1e6);
        messages.add(new AuditRecord(step, (Double) d.get("cost"), d));
    }

    public void record(String step) {
        record(step, new LinkedHashMap<>());
    }

    /** A state field is "filled" when it holds a value. */
    public boolean filled(String field) {
        return switch (field) {
            case "service_name" -> serviceName != null && !serviceName.isEmpty();
            case "context" -> context != null && !context.isEmpty();
            case "build_status" -> buildStatus != null && !buildStatus.isEmpty();
            case "deploys" -> deploys != null && !deploys.isEmpty();
            case "incidents" -> incidents != null && !incidents.isEmpty();
            case "report" -> report != null;
            default -> false;
        };
    }

    /** Read a data field by registry name — the guard's generic accessor. */
    public String field(String name) {
        return switch (name) {
            case "service_name" -> serviceName;
            case "context" -> context;
            case "build_status" -> buildStatus;
            case "deploys" -> deploys;
            case "incidents" -> incidents;
            default -> "";
        };
    }

    /** The recorded path — step names in execution order. */
    public List<String> path() {
        List<String> out = new ArrayList<>();
        for (AuditRecord m : messages) {
            out.add(m.step());
        }
        return out;
    }

    /** Build a detail map from alternating key/value pairs (nulls allowed). */
    public static Map<String,Object> detail(Object... kv) {
        Map<String,Object> m = new LinkedHashMap<>();
        for (int i = 0; i + 1 < kv.length; i += 2) {
            m.put(String.valueOf(kv[i]), kv[i + 1]);
        }
        return m;
    }
}