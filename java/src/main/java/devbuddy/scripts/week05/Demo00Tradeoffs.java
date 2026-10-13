package devbuddy.scripts.week05;

/**
 * Week 5 — Demo 0: The Context Protocol — why REST wasn't enough.
 *
 * <p>Print-only (no LLM, no network). Frames the shift from "a server for my
 * tools" to "a Context Server for any AI client": Resources (read), Prompts
 * (instructions), and Tools (actions).</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week05.Demo00Tradeoffs}</p>
 */
public class Demo00Tradeoffs {

    public static void main(String[] args) {
        System.out.println("=".repeat(70));
        System.out.println("  Demo 0: The Context Protocol — Why REST Wasn't Enough");
        System.out.println("=".repeat(70));
        System.out.println();
        System.out.println("  THE PROBLEM WITH WEEK 4");
        System.out.println("  In Week 4 you built `get_build_status` — a tool (Action).");
        System.out.println("  But the model is still blind: it doesn't know your architecture,");
        System.out.println("  your playbooks, or your SLAs. If you expose only tools, you must");
        System.out.println("  write a bespoke tool for every file. That is unscalable.");
        System.out.println();
        System.out.println("  MCP = Model CONTEXT Protocol. Three primitives:");
        System.out.println("    1. RESOURCES (Read)         — expose files, tables, logs.");
        System.out.println("    2. PROMPTS   (Instructions) — expose standardized workflows.");
        System.out.println("    3. TOOLS     (Actions)      — what you built in Week 4.");
        System.out.println();
        System.out.println("  THE PAYOFF: THE UNIVERSAL CLIENT");
        System.out.println("  Because MCP standardizes Context, you can plug this server into");
        System.out.println("  Claude Desktop, Cursor, or Zed TODAY — zero integration code.");
        System.out.println();
        System.out.println("=".repeat(70));
        System.out.println("  The following demos focus on CONTEXT:");
        System.out.println("    1  Resources & Prompts → the missing pillars of MCP");
        System.out.println("    2  Progressive Discovery → the universal client");
        System.out.println("    3  Protocol Errors → debugging resource/tool failures");
        System.out.println("    4  Security Scope → the blast radius of exposing raw files");
        System.out.println("    5  The Ecosystem Payoff → LLM uses Prompts, Resources, Tools");
        System.out.println("=".repeat(70));
    }
}
