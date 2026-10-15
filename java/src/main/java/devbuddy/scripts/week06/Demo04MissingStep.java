package devbuddy.scripts.week06;

import devbuddy.agent.AgentAnswer;
import devbuddy.agent.AgentState;
import devbuddy.agent.Agents;
import devbuddy.config.AppConfig;
import devbuddy.schemas.EvidenceChunk;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Demo 4 (C2): Missing-Step Hallucination — remove a node, watch it invent.
 *
 * <p>The demo-01 chain with check_build REMOVED and NO guard. The naive
 * report node renders missing state as '{}' and gives the model no ground
 * rules — so when BUILD shows up empty, the model completes the report
 * anyway.</p>
 *
 * <p>Why: the LLM predicts tokens, it doesn't reason about missing data.
 * This is the SAME mechanism as Week 4's tool-error hallucination.</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week06.Demo04MissingStep}</p>
 */
public class Demo04MissingStep {

    private static final String QUERY = "Is payment-api ready for release?";

    /** Structural detection — claims vs STATE, not keyword counting.
     *  Affirmative build claims; hedges ("not checked" etc.) excluded,
     *  because an honest hedge is NOT a hallucination. */
    private static final Pattern AFFIRMATIVE = Pattern.compile(
            "build[^.\\n]{0,60}\\b(healthy|passing|green|success\\w*|degraded|down|failing|compiled)\\b"
                    + "|\\b(healthy|passing|green|compiled)\\b[^.\\n]{0,40}build");
    private static final Pattern HEDGED = Pattern.compile(
            "build[^.\\n]{0,60}(not checked|no (build )?data|never (been )?checked|unknown|missing)"
                    + "|(not checked|no data|never checked)[^.\\n]{0,40}build");

    public static void main(String[] args) {
        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            Agents agents = ctx.getBean(Agents.class);

            DemoSupport.header("Demo 4 (C2): Missing-Step Hallucination");
            System.out.println();
            System.out.println("  The check_build node has been REMOVED from the graph.");
            System.out.println("  state[\"build_status\"] will be \"\" — never checked, no guard.");
            System.out.println("  Watch what the report does with an empty build status.");
            System.out.println();

            DemoSupport.primeIndex(ctx);

            AgentState result = agents.runMissingStepAgent(QUERY);

            System.out.println("  📥  QUERY: \"" + QUERY + "\"");
            System.out.println("  🔀  Path:  " + DemoSupport.path(result));
            System.out.println();
            System.out.println("  [state] build_status = \"" + result.buildStatus + "\"");
            System.out.println("          → Was the build ever checked? "
                    + (result.buildStatus.isEmpty()
                    ? "NO — the node does not exist" : "yes"));
            System.out.println();

            System.out.println("  " + "-".repeat(59));
            System.out.println("  📤  NAIVE REPORT (node rendered BUILD: {}):");
            System.out.println(Agents.formatReport(result.report));
            System.out.println();

            detect(result.report, result.buildStatus);

            // ── The same missing step, with the guard attached ──────────
            System.out.println(DemoSupport.BORDER);
            System.out.println("  SAME missing step — now with the C3 validity guard attached");
            System.out.println(DemoSupport.BORDER);
            System.out.println();

            AgentState guarded = agents.runGuardedChain(QUERY, false);

            System.out.println("  🔀  Path: " + DemoSupport.path(guarded));
            System.out.println("  [state] build_status = \"" + guarded.buildStatus + "\"");
            System.out.println("  🛑  GUARD: " + guarded.error);
            System.out.println();
            System.out.println("  📤  TYPED BLOCKED ANSWER (written by the guard, no LLM):");
            System.out.println(Agents.formatReport(guarded.report));
            System.out.println();
            System.out.println("  The agent REFUSED to produce a confident report from empty state.");
            System.out.println("  Guard = difference between 'tried its best' and 'knew it couldn't'.");
            System.out.println(DemoSupport.BORDER);
            System.out.println();
        }
        System.exit(0);
    }

    /**
     * Structural detection — check claims against STATE, not keywords:
     * an affirmative build claim when state says the build was never
     * checked is a hallucination; a hedge is honest.
     */
    private static void detect(AgentAnswer report, String buildStatus) {
        // 1) fabricated tool evidence: source=tool for build data while
        //    state['build_status'] is empty is a lie the state itself proves.
        List<String> fabricated = new ArrayList<>();
        if (report != null) {
            for (EvidenceChunk e : report.evidence()) {
                if (e.source() == EvidenceChunk.Source.TOOL
                        && e.content().toLowerCase().contains("build")) {
                    fabricated.add(e.content().replace("\n", " "));
                }
            }
        }

        // 2) affirmative vs hedge — over answer + evidence + blockers + steps
        String haystack = haystack(report).toLowerCase();
        Matcher affirmative = AFFIRMATIVE.matcher(haystack);
        Matcher hedged = HEDGED.matcher(haystack);
        boolean hasAffirmative = affirmative.find(); // one find — then reuse
        boolean detected = !fabricated.isEmpty() || hasAffirmative;
        System.out.println("  🔎  DETECTION (state vs. claims — not keyword counting):");
        System.out.println("      state['build_status']      : \"" + buildStatus + "\" (never checked)");
        System.out.println("      fabricated tool evidence   : "
                + (fabricated.isEmpty() ? "none"
                : String.join(" | ", fabricated.stream().map(s -> s.substring(0, Math.min(80, s.length()))).toList())));
        System.out.println("      affirmative build claim    : "
                + (hasAffirmative ? "\"" + affirmative.group() + "\"" : "none"));
        if (hedged.find()) {
            System.out.println("      hedge present              : \"" + hedged.group() + "\"");
        }
        System.out.println();
        if (detected) {
            System.out.println("      → HALLUCINATION: the report asserts (or cites tool evidence for)");
            System.out.println("        build data that state says was never collected. The model");
            System.out.println("        filled a gap YOUR graph left open — it predicts tokens,");
            System.out.println("        it doesn't check state.");
        } else {
            System.out.println("      → The model hedged this run (no affirmative claim). The");
            System.out.println("        VULNERABILITY is still real: nothing in this graph stops");
            System.out.println("        it from inventing. Hedging is luck, not a guardrail.");
        }
        System.out.println();
    }

    private static String haystack(AgentAnswer report) {
        if (report == null) {
            return "";
        }
        StringBuilder sb = new StringBuilder(report.answer());
        if (report.verdict() != null) {
            report.verdict().blockers().forEach(b -> sb.append(' ').append(b));
            report.verdict().recommendedNextSteps().forEach(n -> sb.append(' ').append(n));
        }
        report.evidence().forEach(e -> sb.append(' ').append(e.content()));
        return sb.toString();
    }
}