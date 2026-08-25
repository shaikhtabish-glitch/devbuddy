package devbuddy.scripts.week03;

import devbuddy.config.AppConfig;
import devbuddy.rag.RagService;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;

import java.util.List;

/**
 * Week 3 — Demo 1: Embed → Retrieve → Ground.
 *
 * <p>The full RAG loop, made inspectable: every chunk is printed with its
 * source, the query vector is shown, and the exact system prompt the model
 * receives is displayed. The point is to see the evidence, not just the
 * answer.</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week03.Demo01EmbedRetrieveGround}</p>
 */
public class Demo01EmbedRetrieveGround {

    public static void main(String[] args) {
        try (var ctx = new AnnotationConfigApplicationContext(AppConfig.class)) {
            RagService rag = ctx.getBean(RagService.class);

            String question = "What endpoints does the payment API expose?";
            int k = 4;

            System.out.println("=".repeat(72));
            System.out.println("  Demo 1: Embed → Retrieve → Ground");
            System.out.println("=".repeat(72));
            System.out.println();
            System.out.println("  The RAG loop, step by step:");
            System.out.println("    1. EMBED    — each chunk → a vector (a point in space)");
            System.out.printf("                   model: %s (384-dim vectors)%n", RagService.EMBEDDING_MODEL);
            System.out.println("    2. RETRIEVE — embed the query, return the closest chunks");
            System.out.println("    3. GROUND   — inject those chunks into the prompt, answer");
            System.out.println();
            System.out.println("  Question: " + question);
            System.out.println();

            // ── Step 1: Embed + index ─────────────────────────
            System.out.println("  ── Step 1: Embed & index ────────────────────────────────");
            System.out.println();
            System.out.println("  Each document is split into chunks. Each chunk is embedded");
            System.out.println("  into a vector and stored in Qdrant.");
            System.out.println();
            int count = rag.indexDocuments(null, 512, 64);
            System.out.println("  ✅ Indexed " + count + " chunks → collection 'devbuddy-docs'");
            System.out.println();

            // ── Step 2: Retrieve ──────────────────────────────
            System.out.println("  ── Step 2: Retrieve (top-k by vector similarity) ────────");
            System.out.println();
            System.out.println("  The request — the query — is also embedded into a vector:");
            System.out.println();
            System.out.println("    \"" + question + "\"");
            float[] queryVector = rag.embedText(question);
            StringBuilder preview = new StringBuilder("[");
            for (int i = 0; i < Math.min(5, queryVector.length); i++) {
                if (i > 0) {
                    preview.append(", ");
                }
                preview.append(String.format("%.4f", queryVector[i]));
            }
            preview.append("] ...");
            System.out.println("    → " + queryVector.length + "-dim vector: " + preview);
            System.out.println();
            System.out.println("  Qdrant returns the " + k + " chunks whose vectors are closest to");
            System.out.println("  that query vector, most relevant first. The source of each");
            System.out.println("  chunk is shown so you can trace it back:");
            System.out.println();

            List<RagService.RetrievedChunk> chunks = rag.retrieveWithSources(question, k);
            for (int i = 0; i < chunks.size(); i++) {
                RagService.RetrievedChunk c = chunks.get(i);
                System.out.println("  [" + (i + 1) + "] " + c.source());
                System.out.println("      " + c.content());
                System.out.println();
            }

            // ── Step 3: Ground ────────────────────────────────
            System.out.println("  ── Step 3: Ground (chunks → prompt → LLM) ───────────────");
            System.out.println();
            System.out.println("  The chunks above are injected VERBATIM into the system prompt");
            System.out.println("  as CONTEXT. This is the exact prompt the model receives:");
            System.out.println();
            String promptPreview = RagService.SYSTEM_PROMPT.formatted(
                    "<the " + k + " chunks from Step 2, joined with '---'>");
            for (String line : promptPreview.split("\n")) {
                System.out.println("  │ " + line);
            }
            System.out.println();
            System.out.println("  ── user message ──");
            System.out.println("  │ " + question);
            System.out.println();

            String answer = rag.groundedAnswerFromChunks(
                    question, chunks.stream().map(RagService.RetrievedChunk::content).toList(), 0.0);
            System.out.println("  ── answer ──");
            System.out.println("  │ " + answer);
            System.out.println();

            // ── Verify ────────────────────────────────────────
            System.out.println("=".repeat(72));
            System.out.println("  Verify the grounding:");
            System.out.println("  every endpoint in the answer should appear in the chunks above.");
            System.out.println("  The chunks are the evidence — check them, not the model's");
            System.out.println("  confidence.");
            System.out.println("=".repeat(72));
        }
    }
}
