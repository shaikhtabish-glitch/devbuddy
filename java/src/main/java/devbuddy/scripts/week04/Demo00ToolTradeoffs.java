package devbuddy.scripts.week04;

/**
 * Week 4 — Demo 0: Tool Use — tradeoffs & when NOT to use it.
 *
 * <p>Print-only (no LLM, no network). Frames the boundary, the pros, the
 * cons, and the judgment call that the other five demos make concrete.</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week04.Demo00ToolTradeoffs}</p>
 */
public class Demo00ToolTradeoffs {

    public static void main(String[] args) {
        System.out.println("=".repeat(70));
        System.out.println("  Demo 0: Tool Use — Tradeoffs & When NOT to Use It");
        System.out.println("=".repeat(70));
        System.out.println();
        System.out.println("  THE BOUNDARY");
        System.out.println("  The model never runs your code. It returns a REQUEST ({name, args});");
        System.out.println("  your application decides whether that request becomes an action.");
        System.out.println("  Safety never comes from the model — it comes from the boundary you draw:");
        System.out.println("  whitelist, validation, retry, denial, audit log.");
        System.out.println();
        System.out.println("  The loop");
        System.out.println("  Request → Decide (model) → Execute (your code) → Return → Answer");
        System.out.println("  Every round-trip = another LLM call = latency + tokens.");
        System.out.println();
        System.out.println("  PROS — live data · grounded decisions · extensible · auditable");
        System.out.println();
        System.out.println("  CONS");
        System.out.println("  • LATENCY — each tool round adds a full LLM call.");
        System.out.println("  • COST — tool results re-enter context; tokens compound per round.");
        System.out.println("  • A NEW FAILURE SURFACE — tools crash, time out, return bad data.");
        System.out.println("  • MISROUTING — wrong tool, or a needed tool skipped.");
        System.out.println("  • INJECTION SURFACE — your whitelist is the only defence.");
        System.out.println();
        System.out.println("  WHEN NOT TO USE TOOL CALLING");
        System.out.println("  • Deterministic pipeline (A then B then C) → just write code.");
        System.out.println("  • One tool, always the same call → call the function directly.");
        System.out.println("  • Sub-100ms, zero-failure critical paths → no LLM in the loop.");
        System.out.println();
        System.out.println("  WHERE THE CONTROL LIVES (say this out loud)");
        System.out.println("  Which tool / args  → model decides; MY descriptions trained it.");
        System.out.println("  Whether it runs    → MY whitelist, not the model.");
        System.out.println("  Retry / denial     → CODE decisions, deterministic and testable.");
        System.out.println("  Cost / audit       → MY trace and a bounded loop.");
        System.out.println("=".repeat(70));
    }
}
