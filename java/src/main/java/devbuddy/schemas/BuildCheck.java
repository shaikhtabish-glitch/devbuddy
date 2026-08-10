package devbuddy.schemas;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * A build status check — the kind DevBuddy will generate autonomously by Week 6.
 *
 * Equivalent to:
 * <ul>
 *   <li>Python: {@code BuildCheck(BaseModel)} in {@code verification.py}</li>
 *   <li>Node.js: {@code BuildCheckSchema} Zod schema in {@code verification.js}</li>
 * </ul>
 *
 * Uses Jakarta Bean Validation for the typed contract (Java's answer to
 * Pydantic / Zod). The {@code @JsonProperty} annotations map to the
 * lowercase values the LLM is prompted to return.
 */
public record BuildCheck(

        @JsonProperty("project")
        String project,

        @JsonProperty("status")
        Status status,

        @JsonProperty("confidence")
        double confidence,

        @JsonProperty("explanation")
        String explanation
) {

    public enum Status {
        @JsonProperty("passing")      PASSING,
        @JsonProperty("failing")      FAILING,
        @JsonProperty("in_progress")  IN_PROGRESS,
        @JsonProperty("unknown")      UNKNOWN
    }
}
