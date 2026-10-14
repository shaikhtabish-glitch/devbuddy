package devbuddy.agent;

/**
 * Guard 1 — the budget: steps/cost ceiling (operational).
 *
 * <p>Mutable statics on purpose: demo-05 mutates the ceiling to 2, runs an
 * agent, then restores it — the same teaching move as Python's module-level
 * {@code _BUDGET} and Node's exported {@code BUDGET} object.</p>
 */
public final class Budget {

    private Budget() {
    }

    public static int maxSteps = 10;
    public static double maxCost = 2.0;

    /** Trip check — the plan node asks BEFORE proposing anything. */
    public static boolean exceeded(AgentState state) {
        return state.steps >= maxSteps || state.cost >= maxCost;
    }
}