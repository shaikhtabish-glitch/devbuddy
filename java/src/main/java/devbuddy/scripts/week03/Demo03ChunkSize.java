package devbuddy.scripts.week03;

import devbuddy.rag.EmbeddingService;
import devbuddy.rag.RagService;

import java.util.ArrayList;
import java.util.List;

/**
 * Week 3 — Demo 3: Chunking — how chunk size changes what gets retrieved.
 *
 * <p>Indexes the same documents three times — chunk size 256, 512, 1024 — and
 * retrieves the top-3 chunks for the SAME question each time. Only the chunk
 * size changes; the question, the embeddings, and the retriever are identical.</p>
 *
 * <p>Watch two things at each size: how many chunks the index holds, and which
 * documents the retrieved chunks come from (and how long they are).</p>
 *
 * <p>Run: {@code mvn -q compile exec:java -Dexec.mainClass=devbuddy.scripts.week03.Demo03ChunkSize}</p>
 */
public class Demo03ChunkSize {

    public static void main(String[] args) {
        // No LLM calls in this demo — build the RAG pipeline directly (no API key needed).
        try (RagService rag = new RagService(null, "openai/gpt-4o-mini",
                new EmbeddingService(), "localhost", 6334)) {

            String question = "How do I set up DevBuddy?";
            // The answer to this question lives in CONTRIBUTING.md — so chunks
            // from other files are noise. (A fact about the corpus, not a verdict.)
            String answerDoc = "CONTRIBUTING.md";
            int k = 3;
            int[] sizes = {256, 512, 1024};

            System.out.println("=".repeat(72));
            System.out.println("  Demo 3: Chunk Size — Same Question, Different Retrieval");
            System.out.println("=".repeat(72));
            System.out.println();
            System.out.println("  Question: \"" + question + "\"");
            System.out.println();
            System.out.println("  The documents are indexed three times, once per chunk size.");
            System.out.println("  The question and the retriever do not change — only chunk size.");
            System.out.println();
            System.out.println("  The answer to this question lives in " + answerDoc + ";");
            System.out.println("  chunks from other files are noise.");
            System.out.println();

            // Why do unrelated docs (e.g. payment-api-spec.md) appear in the results?
            //
            // The retriever is a top-k nearest-neighbour search: it must return
            // exactly K chunks and has NO relevance gate. For this question the
            // genuinely close chunks are all in CONTRIBUTING.md (scores
            // ~0.40 / 0.25 / 0.24). Once those run out, slot K gets filled by
            // whatever is vector-closest next — and that is payment-api-spec.md
            // at ~0.17 (incident-log is ~0.10, lower still).
            //
            // "Closest in embedding space" != "topically relevant". The score
            // cliff (0.40 → 0.17) is the retriever's way of saying "best I
            // have left".
            //
            // Chunk size decides HOW the noise leaks in:
            //   • 256/1024 → only 2 CONTRIBUTING chunks outscore
            //     payment-api-spec.md, so it slips into slot 3 (as a 199-char
            //     endpoint shard or the whole 828-char spec).
            //   • 512      → exactly 3 CONTRIBUTING chunks outscore it, so it
            //     lands at slot 4 and stays invisible.
            //
            // The chunk itself doesn't get more relevant — chunk size just
            // reshuffles which chunks exist, and a vacant top-K slot gets
            // filled with noise.
            List<int[]> summary = new ArrayList<>(); // {size, count, avgLen}

            for (int size : sizes) {
                int count = rag.indexDocuments(null, size, 64);
                List<RagService.RetrievedChunk> chunks = rag.retrieveWithSources(question, k);
                int avgLen = chunks.isEmpty() ? 0
                        : chunks.stream().mapToInt(c -> c.content().length()).sum() / chunks.size();
                summary.add(new int[]{size, count, avgLen});

                System.out.println("  ── chunk_size = " + size + "   (" + count + " chunks indexed) ──");
                System.out.println();
                for (int i = 0; i < chunks.size(); i++) {
                    RagService.RetrievedChunk c = chunks.get(i);
                    String note = c.source().equals(answerDoc) ? "" : "   ← other document";
                    System.out.println("  [" + (i + 1) + "] " + c.source()
                            + "  (" + c.content().length() + " chars)" + note);
                    System.out.println("      " + c.content());
                    System.out.println();
                }
                System.out.println();
            }

            // ── Summary ──────────────────────────────────────
            System.out.println("=".repeat(72));
            System.out.println("  SUMMARY");
            System.out.println("=".repeat(72));
            System.out.println();
            System.out.printf("  %-12s %-16s %-20s%n", "chunk_size", "chunks indexed", "avg retrieved len");
            System.out.printf("  %-12s %-16s %-20s%n", "─".repeat(12), "─".repeat(16), "─".repeat(20));
            for (int[] row : summary) {
                System.out.printf("  %-12d %-16d %-20d%n", row[0], row[1], row[2]);
            }
            System.out.println();
            System.out.println("  The tradeoff, in general:");
            System.out.println("    smaller → more chunks, each tighter, but context can be split");
            System.out.println("              (e.g. a bare '# Title' with no body).");
            System.out.println("    larger  → fewer chunks, but unrelated content can ride along");
            System.out.println("              (e.g. a whole payment API spec in a setup answer).");
            System.out.println();
            System.out.println("  Look back at the sources and lengths above and decide where the");
            System.out.println("  balance sits for THESE documents. There is no universal answer.");
            System.out.println("=".repeat(72));
        }
    }
}
