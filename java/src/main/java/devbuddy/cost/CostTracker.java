package devbuddy.cost;

import java.util.Map;

/**
 * Token-to-cost calculation for OpenRouter models.
 *
 * Equivalent to:
 * <ul>
 *   <li>Node.js: {@code config.js} pricing table + {@code calculateCost()}</li>
 *   <li>Python: inline cost calculation in {@code verification.py}</li>
 * </ul>
 *
 * <p>Pricing is per 1M tokens (OpenRouter rates). Add new models here
 * as the curriculum progresses through provider swaps.</p>
 */
public final class CostTracker {

    private record Pricing(double input, double output) {}

    private static final Map<String, Pricing> PRICING = Map.of(
            "openai/gpt-4o-mini",           new Pricing(0.15,  0.60),
            "anthropic/claude-3.5-sonnet",  new Pricing(3.00, 15.00),
            "google/gemini-2.5-flash-lite", new Pricing(0.075, 0.30)
    );

    private static final Pricing DEFAULT_PRICING = new Pricing(0.15, 0.60);

    private CostTracker() {
        // utility class — no instances
    }

    /**
     * Calculate cost in USD from token counts.
     *
     * @param model           OpenRouter model string (e.g. "openai/gpt-4o-mini")
     * @param promptTokens     number of input/prompt tokens used
     * @param completionTokens number of output/completion tokens used
     * @return estimated cost in USD
     */
    public static double calculateCost(String model, long promptTokens, long completionTokens) {
        Pricing pricing = PRICING.getOrDefault(model, DEFAULT_PRICING);
        return (promptTokens * pricing.input() + completionTokens * pricing.output()) / 1_000_000.0;
    }
}
