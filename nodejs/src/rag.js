/**
 * Week 3 — RAG Pipeline: Embed, Chunk, Store, Retrieve, Ground (Node.js)
 *
 * Uses @xenova/transformers (all-MiniLM-L6-v2) for embeddings — local, free, no API cost.
 * Qdrant for vector storage — runs in Docker, cross-language.
 * Hybrid search with BM25 + vector for exact keyword matching.
 *
 * Imports: import { getLlm } from "./llm.js"
 */
import { readFileSync, readdirSync } from "fs";
import { resolve, extname, dirname, basename } from "path";
import { fileURLToPath } from "url";
import { HuggingFaceTransformersEmbeddings } from "@langchain/community/embeddings/huggingface_transformers";
import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";
import { QdrantVectorStore } from "@langchain/qdrant";
import { QdrantClient } from "@qdrant/js-client-rest";
import { Document } from "@langchain/core/documents";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { getLlm } from "./llm.js";

// ─── Config ───────────────────────────────────────────────────
const EMBEDDING_MODEL = "Xenova/all-MiniLM-L6-v2";
const QDRANT_URL = process.env.QDRANT_URL || "http://localhost:6333";
const QDRANT_COLLECTION = "devbuddy-docs";
const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = resolve(__dirname, "..", "..", "shared", "data");

// RRF fusion constant — single source of truth (demos import this).
export const RRF_K = 60;

// The system prompt is the guardrail: it constrains the model to the
// retrieved context and tells it to decline out-of-corpus questions.
export const SYSTEM_PROMPT =
  "You are a knowledge base assistant. Answer the user's question " +
  "using ONLY the provided context below. If the context does not " +
  "contain the answer, say 'I don't have information about that in " +
  "my knowledge base.' Never invent information.\n\n" +
  "CONTEXT:\n" +
  "{context}";

// The SAME prompt with the guardrail removed — used to show what happens
// without it (the model is no longer told to decline).
export const NO_GUARDRAIL_PROMPT =
  "You are a helpful assistant. Answer the user's question, even if you " +
  "have to make reasonable assumptions. Be specific.\n\n" +
  "CONTEXT:\n" +
  "{context}";

let _embeddings = null;
let _vectorstore = null;
let _documents = null;

// ─── Helpers ──────────────────────────────────────────────────

async function _getEmbeddings() {
  if (!_embeddings) {
    _embeddings = new HuggingFaceTransformersEmbeddings({
      model: EMBEDDING_MODEL,
    });
  }
  return _embeddings;
}

function _loadDocuments(directory) {
  /**
   * Load .md and .txt files from a directory into Document objects.
   * Returns an array of Document instances.
   */
  const files = [];
  try {
    const entries = readdirSync(directory);
    for (const entry of entries) {
      const ext = extname(entry).toLowerCase();
      if (ext === ".md" || ext === ".txt") {
        const filePath = resolve(directory, entry);
        const content = readFileSync(filePath, "utf-8");
        files.push(
          new Document({
            pageContent: content,
            metadata: { source: entry },
          })
        );
      }
    }
  } catch (e) {
    throw new Error(
      `Failed to load documents from ${directory}: ${e.message}`
    );
  }

  if (files.length === 0) {
    throw new Error(`No .md or .txt files found in ${directory}`);
  }
  return files;
}

/**
 * Lowercase and split on non-alphanumerics.
 *
 * The naive preprocessing is `text.split(/\s+/)`, which keeps case and does
 * not split hyphens — so "INC-799" becomes a single token and only chunks
 * containing that exact string score above zero. Splitting on
 * non-alphanumerics makes "INC-799" match "inc" + "799" and fixes case
 * sensitivity (the reason exact-ID queries missed their targets).
 */
export function _bm25Tokenize(text) {
  return text.toLowerCase().match(/[a-z0-9]+/g) || [];
}

/**
 * True if a chunk is only a heading + blockquote metadata (no body).
 *
 * Header chunks score high in vector search but carry no answer content
 * (e.g. "# Payment API — Internal Specification" + owner/date metadata).
 * We drop them at index time so they don't crowd out the real evidence.
 */
export function _isTitleOnly(text) {
  const bodyWords = [];
  for (const line of text.split("\n")) {
    const stripped = line.trim();
    if (!stripped || stripped.startsWith("#") || stripped.startsWith(">")) {
      continue;
    }
    bodyWords.push(...stripped.split(/\s+/));
  }
  return bodyWords.length < 8;
}

/** Format a prompt template containing a {context} slot. */
export function formatPrompt(template, context) {
  return template.replace("{context}", () => context);
}

// ─── Public API ───────────────────────────────────────────────

/**
 * Load .md and .txt files, chunk them, embed them, and store in Qdrant.
 *
 * @param {string|null} [directory] - Path to document directory. Defaults to shared/data/.
 * @param {number} [chunkSize=512] - Max tokens per chunk.
 * @param {number} [chunkOverlap=64] - Overlapping tokens between chunks.
 * @returns {Promise<number>} Number of chunks indexed.
 */
export async function indexDocuments(
  directory = null,
  chunkSize = 512,
  chunkOverlap = 64
) {
  const target = directory || DATA_DIR;
  const docs = _loadDocuments(target);

  const splitter = new RecursiveCharacterTextSplitter({
    chunkSize,
    chunkOverlap,
    separators: ["\n# ", "\n## ", "\n### ", "\n#### ", "\n", " ", ""],
  });

  let chunks = await splitter.splitDocuments(docs);

  // Drop heading-only chunks: they rank high on similarity but contain no
  // answer content (a bare "# Title" + date/owner metadata).
  chunks = chunks.filter((c) => !_isTitleOnly(c.pageContent));

  const emb = await _getEmbeddings();

  // Clear the collection points if it exists to ensure a fresh index without recreation conflicts
  const client = new QdrantClient({ url: QDRANT_URL });
  try {
    await client.delete(QDRANT_COLLECTION, {
      filter: {},
      wait: true,
    });
  } catch (e) {
    // Collection might not exist, ignore
  }

  // Connect to Qdrant, recreate collection with fresh vectors
  _vectorstore = await QdrantVectorStore.fromDocuments(chunks, emb, {
    url: QDRANT_URL,
    collectionName: QDRANT_COLLECTION,
  });

  _documents = chunks;
  return chunks.length;
}

/**
 * Embed a single piece of text into a vector (for inspection / demos).
 *
 * @param {string} text - The text to embed.
 * @returns {Promise<number[]>} The embedding vector.
 */
export async function embedText(text) {
  const emb = await _getEmbeddings();
  return emb.embedQuery(text);
}

/**
 * Retrieve the top-k most relevant chunks for a query.
 *
 * @param {string} query - The search query.
 * @param {number} [k=3] - Number of chunks to return.
 * @returns {Promise<string[]>} List of chunk content strings, most relevant first.
 */
export async function retrieve(query, k = 3) {
  if (!_vectorstore) {
    throw new Error("No index found. Run indexDocuments() first.");
  }
  const results = await _vectorstore.similaritySearch(query, k);
  return results.map((doc) => doc.pageContent);
}

/**
 * Retrieve the top-k chunks together with source and similarity score.
 *
 * @param {string} query - The search query.
 * @param {number} [k=3] - Number of chunks to return.
 * @param {number|null} [minScore=null] - Optional cosine-similarity cutoff.
 *   Chunks below this score are dropped. Vector search is a top-k
 *   nearest-neighbour query with no "not found" concept, so without a cutoff
 *   it always returns k chunks — even irrelevant ones. Set this to turn
 *   "best guess" into "no match".
 * @returns {Promise<Array<{content: string, source: string, score: number}>>}
 */
export async function retrieveWithSources(query, k = 3, minScore = null) {
  if (!_vectorstore) {
    throw new Error("No index found. Run indexDocuments() first.");
  }
  let results = await _vectorstore.similaritySearchWithScore(query, k);
  if (minScore !== null) {
    results = results.filter(([, score]) => score >= minScore);
  }
  return results.map(([doc, score]) => ({
    content: doc.pageContent,
    source: basename(doc.metadata?.source || "unknown"),
    score,
  }));
}

/**
 * Simple BM25-inspired keyword search over the loaded documents.
 * Scores documents by term frequency of tokenized query words.
 */
function _bm25Search(query, documents, k) {
  const queryTerms = _bm25Tokenize(query);
  const scored = documents.map((doc) => {
    const tokens = _bm25Tokenize(doc.pageContent);
    const counts = new Map();
    for (const token of tokens) {
      counts.set(token, (counts.get(token) || 0) + 1);
    }
    let score = 0;
    for (const term of queryTerms) {
      score += counts.get(term) || 0;
    }
    return { text: doc.pageContent, score };
  });

  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, k).map((s) => s.text);
}

/**
 * hybridSearch() plus the internals: for every final hit, report its rank in
 * EACH retriever (null = that retriever never ranked it) and the fused RRF
 * score.
 *
 * RRF (reciprocal rank fusion): score = sum over retrievers of
 * 1 / (RRF_K + rank). A chunk ranked #1 by BM25 and #7 by vector scores
 * 1/61 + 1/67 — which is why a hit one side ranks #1 can still surface
 * even when the other side ranks it lower.
 *
 * @param {string} query - The search query.
 * @param {number} [k=3] - Number of chunks to return after merging.
 * @returns {Promise<Array<{content, source, vec_rank, bm25_rank, rrf_score}>>}
 */
export async function hybridSearchWithScores(query, k = 3) {
  if (!_vectorstore || !_documents) {
    throw new Error("No index found. Run indexDocuments() first.");
  }

  // Per-retriever candidate lists (top k*2 each). A chunk that one side
  // misses entirely is a "blind spot" — reported as a null rank.
  const vecResults = await _vectorstore.similaritySearch(query, k * 2);
  const vecChunks = vecResults.map((doc) => doc.pageContent);
  const bm25Chunks = _bm25Search(query, _documents, k * 2);

  const sources = new Map();
  for (const doc of _documents) {
    sources.set(doc.pageContent, basename(doc.metadata?.source || "unknown"));
  }

  const rrfScores = new Map();
  const addScore = (chunk, rank) => {
    rrfScores.set(chunk, (rrfScores.get(chunk) || 0) + 1.0 / (RRF_K + rank));
  };
  vecChunks.forEach((chunk, i) => addScore(chunk, i + 1));
  bm25Chunks.forEach((chunk, i) => addScore(chunk, i + 1));

  return [...rrfScores.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, k)
    .map(([chunk, score]) => ({
      content: chunk,
      source: sources.get(chunk) || "unknown",
      vec_rank: vecChunks.includes(chunk) ? vecChunks.indexOf(chunk) + 1 : null,
      bm25_rank: bm25Chunks.includes(chunk) ? bm25Chunks.indexOf(chunk) + 1 : null,
      rrf_score: score,
    }));
}

/**
 * Retrieve using BM25 (keyword) + vector (semantic) and merge via RRF.
 *
 * BM25 catches exact names, IDs, error codes. Vector catches meaning.
 * RRF fusion combines both rankings into one result set.
 *
 * @param {string} query - The search query.
 * @param {number} [k=3] - Number of chunks to return after merging.
 * @returns {Promise<string[]>} List of chunk content strings, merged via RRF.
 */
export async function hybridSearch(query, k = 3) {
  const results = await hybridSearchWithScores(query, k);
  return results.map((r) => r.content);
}

/**
 * The "augment + generate" step: inject ALREADY-RETRIEVED chunks into a
 * system prompt and ask the LLM to answer. The system prompt is the
 * guardrail — pass SYSTEM_PROMPT to ground, or NO_GUARDRAIL_PROMPT to see
 * what the model does without it.
 *
 * Kept separate from retrieval so callers can inspect (and display) the
 * exact chunks that ground the answer before sending them to the model.
 *
 * @param {string} query - The user's question.
 * @param {string[]} chunks - Pre-retrieved chunk contents.
 * @param {string} [systemPrompt=SYSTEM_PROMPT] - Prompt template with a {context} slot.
 * @param {number} [temperature=0.0] - 0.0 for deterministic output.
 * @param {number} [maxTokens] - Max tokens in LLM response.
 * @returns {Promise<string>} The LLM's answer.
 */
export async function answerWithContext(
  query,
  chunks,
  systemPrompt = SYSTEM_PROMPT,
  temperature = 0.0,
  maxTokens
) {
  const context = chunks.join("\n\n---\n\n");
  const llm = getLlm({ temperature, maxTokens });
  const response = await llm.invoke([
    new SystemMessage(formatPrompt(systemPrompt, context)),
    new HumanMessage(query),
  ]);
  return response.content.trim();
}

/**
 * Ground an answer using SYSTEM_PROMPT (the guardrail).
 * See answerWithContext.
 */
export async function groundedAnswerFromChunks(query, chunks, temperature = 0.0) {
  return answerWithContext(query, chunks, SYSTEM_PROMPT, temperature);
}

/**
 * Answer a question grounded in the retrieved context.
 *
 * Retrieves top-k chunks, injects them into the prompt, and asks the LLM
 * to answer strictly from the provided context.
 *
 * @param {string} query - The user's question.
 * @param {number} [k=3] - Number of chunks to retrieve.
 * @param {number} [temperature=0.0] - 0.0 for deterministic output.
 * @param {number} [maxTokens=500] - Max tokens in LLM response.
 * @returns {Promise<string>} The LLM's answer, grounded in retrieved documents.
 */
export async function groundedAnswer(query, k = 3, temperature = 0.0, maxTokens = 500) {
  const chunks = await retrieve(query, k);
  return answerWithContext(query, chunks, SYSTEM_PROMPT, temperature, maxTokens);
}

/**
 * Same as groundedAnswer, but also returns the retrieved chunks
 * for transparency — engineers can verify the grounding.
 *
 * @param {string} query - The user's question.
 * @param {number} [k=3] - Number of chunks to retrieve.
 * @param {number} [temperature=0.0] - 0.0 for deterministic output.
 * @param {number} [maxTokens=500] - Max tokens in LLM response.
 * @returns {Promise<[string, string[]]>} Tuple of [answer, retrieved chunks].
 */
export async function groundedAnswerWithChunks(
  query,
  k = 3,
  temperature = 0.0,
  maxTokens = 500
) {
  const chunks = await retrieve(query, k);
  const answer = await answerWithContext(query, chunks, SYSTEM_PROMPT, temperature, maxTokens);
  return [answer, chunks];
}
