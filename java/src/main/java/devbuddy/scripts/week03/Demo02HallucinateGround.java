package devbuddy.scripts.week03;

import devbuddy.config.AppConfig;
import devbuddy.rag.RagService;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

import java.util.List;

/**
 * Week 3 — Demo 2: Hallucinate → Ground.
 *
 * <p>The system prompt is the guardrail. This demo proves it by holding the
 * question AND the retrieved chunks fixed, and changing only the system prompt:
 * out-of-corpus + guardrail → the model declines; out-of-corpus without
 * guardrail → the model hallucinates; in-corpus + guardrail → the model answers
 * from the chunks.</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week03.Demo02HallucinateGround}</p>
 */
public class Demo02HallucinateGround {

    public static void main(String[] args) {
        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            RagService rag = ctx.getBean(RagService.class);

            String outOfCorpus = "What's the revenue forecast for Q4 2028?";
            String inCorpus = "How do I contribute code to DevBuddy?";
            int k = 3;

            System.out.println("=".repeat(72));
            System.out.println("  Demo 2: Hallucinate → Ground");
            System.out.println("=".repeat(72));
            System.out.println();

            rag.indexDocuments(null, 512, 64);
            System.out.println("  ✅ Index ready");
            System.out.println();

            // ── The out-of-corpus retrieval ───────────────────
            // WHY does the retriever return "random" info for an out-of-corpus
            // question ("Q4 2028 revenue") instead of nothing?
            //
            // Because vector search is a top-k nearest-neighbour query: it ALWAYS
            // returns k chunks and has no "not found" concept and no relevance
            // cutoff. For this question the query vector points into an empty
            // region of vector space, so the "nearest" chunks are still far away
            // (scores ~0.30 / 0.27 / 0.22, vs ~0.60 for an in-corpus question)
            // and happen to be about payments, incidents and SLAs.
            //
            // Similarity is a RELATIVE ranking, not an ABSOLUTE relevance
            // judgement: Qdrant sorts everything by distance and hands back the
            // top-k. It never says "0.22 is too low to be useful — nothing
            // matched". That decision is left to the guardrail below.
            System.out.println("  Out-of-corpus question: \"" + outOfCorpus + "\"");
            System.out.println();
            System.out.println("  The retriever always returns its top-" + k + " chunks — even when none");
            System.out.println("  of them answer the question:");
            System.out.println();

            List<RagService.RetrievedChunk> chunks = rag.retrieveWithSources(outOfCorpus, k);
            for (int i = 0; i < chunks.size(); i++) {
                System.out.println("  [" + (i + 1) + "] " + chunks.get(i).source());
                System.out.println("      " + chunks.get(i).content());
                System.out.println();
            }
            System.out.println("  None of these mention Q4 2028 revenue. Retrieval can't return");
            System.out.println("  \"nothing\" — it returns its best (irrelevant) guess.");
            System.out.println();

            // ── With the guardrail ────────────────────────────
            System.out.println("  ── With the guardrail ───────────────────────────────────");
            System.out.println();
            System.out.println("  The system prompt tells the model to decline when the context");
            System.out.println("  doesn't contain the answer:");
            System.out.println();
            printPrompt(RagService.SYSTEM_PROMPT.formatted("<the " + k + " chunks above>"));
            System.out.println();
            String guarded = rag.answerWithContext(
                    outOfCorpus, chunkContents(chunks), RagService.SYSTEM_PROMPT, 0.0);
            System.out.println("  Answer: " + guarded);
            System.out.println();

            // ── Without the guardrail ─────────────────────────
            System.out.println("  ── Without the guardrail ────────────────────────────────");
            System.out.println();
            System.out.println("  Same question, same chunks — but the decline instruction is gone:");
            System.out.println();
            printPrompt(RagService.NO_GUARDRAIL_PROMPT.formatted("<the " + k + " chunks above>"));
            System.out.println();
            String unguarded = rag.answerWithContext(
                    outOfCorpus, chunkContents(chunks), RagService.NO_GUARDRAIL_PROMPT, 0.0);
            System.out.println("  Answer: " + unguarded);
            System.out.println();

            // ── In-corpus ─────────────────────────────────────
            System.out.println("  ── In-corpus (grounded) ─────────────────────────────────");
            System.out.println();
            System.out.println("  Question: \"" + inCorpus + "\"");
            System.out.println();
            List<RagService.RetrievedChunk> groundedChunks = rag.retrieveWithSources(inCorpus, k);
            for (int i = 0; i < groundedChunks.size(); i++) {
                System.out.println("  [" + (i + 1) + "] " + groundedChunks.get(i).source());
                System.out.println("      " + groundedChunks.get(i).content());
                System.out.println();
            }
            String grounded = rag.answerWithContext(
                    inCorpus, chunkContents(groundedChunks), RagService.SYSTEM_PROMPT, 0.0);
            System.out.println("  Answer: " + grounded);
            System.out.println();

            System.out.println("=".repeat(72));
            System.out.println("  Same retriever. Same chunks. Only the system prompt changed.");
            System.out.println("  The guardrail is what separates a hallucination from a refusal.");
            System.out.println("=".repeat(72));
        }
    }

    private static List<String> chunkContents(List<RagService.RetrievedChunk> chunks) {
        return chunks.stream().map(RagService.RetrievedChunk::content).toList();
    }

    private static void printPrompt(String prompt) {
        for (String line : prompt.split("\n")) {
            System.out.println("  │ " + line);
        }
    }
}
