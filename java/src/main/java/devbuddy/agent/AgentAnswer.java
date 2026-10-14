package devbuddy.agent;

import devbuddy.schemas.EvidenceChunk;
import devbuddy.schemas.ReadinessVerdict;

import java.util.List;

/**
 * Week 6 — the agent's structured answer to any query.
 *
 * <p>The Node sibling of Python's {@code AgentAnswer} model (schemas.py) and
 * Node's {@code AgentAnswerSchema} (schemas.js):</p>
 * <ul>
 *   <li>{@code answer}  — the direct response, always present.</li>
 *   <li>{@code verdict} — Week 2's {@link ReadinessVerdict}, reused not
 *       redefined. {@code null} for docs/deploy/incident queries where
 *       "ready" is meaningless.</li>
 *   <li>{@code evidence} — Week 2's {@link EvidenceChunk} contract.</li>
 * </ul>
 *
 * <p>Cross-field rules mirror Python's {@code verdict_sanity_check} exactly —
 * an answer where the model contradicts itself is REJECTED at the boundary:</p>
 * <ol>
 *   <li>{@code ready=true} + non-empty blockers → reject</li>
 *   <li>{@code ready=false} + {@code confidence != low} + no blockers → reject</li>
 * </ol>
 */
public record AgentAnswer(
        String answer,
        ReadinessVerdict verdict,
        List<EvidenceChunk> evidence
) {

    public AgentAnswer {
        answer = answer == null ? "" : answer;
        evidence = evidence == null ? List.of() : evidence;

        if (verdict != null) {
            if (verdict.ready() && !verdict.blockers().isEmpty()) {
                throw new IllegalArgumentException(
                        "Contradiction: verdict.ready=true but blockers=" + verdict.blockers()
                                + ". If there are blockers, ready must be false.");
            }
            if (!verdict.ready()
                    && verdict.confidence() != ReadinessVerdict.Confidence.LOW
                    && verdict.blockers().isEmpty()) {
                throw new IllegalArgumentException(
                        "verdict.ready=false with confidence='" + verdict.confidence().value()
                                + "' but no blockers listed. Add blockers or lower confidence.");
            }
        }
    }

    /** Convenience: an AgentAnswer with no verdict (docs-style answers). */
    public static AgentAnswer of(String answer) {
        return new AgentAnswer(answer, null, List.of());
    }
}