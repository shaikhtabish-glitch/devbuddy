package devbuddy.agent;

import java.util.Map;

/**
 * One audit event: which step ran, what it did, what it cost.
 *
 * <p>{@code detail} is the node's self-report (e.g. {@code proposal},
 * {@code decision}, {@code reason} for plan records; {@code status},
 * {@code category} for guard records). Demos print it verbatim — the trail
 * is recorded by the nodes, never reconstructed after the fact.</p>
 */
public record AuditRecord(String step, double cost, Map<String, Object> detail) {

    @SuppressWarnings("unchecked")
    public <T> T get(String key) {
        return (T) detail.get(key);
    }

    public String getString(String key) {
        Object v = detail.get(key);
        return v == null ? null : String.valueOf(v);
    }
}