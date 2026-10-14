package devbuddy.agent;

/**
 * Structured tool failure — transport error or failure payload.
 *
 * <p>Node equivalents: thrown by {@code callMcpTool}. Python: {@code
 * ToolFailure}. Never a crash: the calling node records it in the audit
 * trail and the run continues with the field left empty.</p>
 */
public class ToolFailure extends RuntimeException {

    public ToolFailure(String message) {
        super(message);
    }
}