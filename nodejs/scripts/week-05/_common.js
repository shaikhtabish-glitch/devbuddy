/**
 * Shared helpers for the Week 5 MCP demos (Node.js).
 *
 * Keeps each demo focused on the lesson: consistent borders, a pause()
 * that degrades gracefully in non-interactive runs, and the MCP URL.
 */
import readline from "node:readline";

export const BORDER = "=".repeat(70);
export const MCP_URL = process.env.MCP_URL || "http://127.0.0.1:3001/sse";

// Per-request timeout for tool calls. Tool handlers synthesise answers with
// the LLM, which can take longer than the SDK's 60s default on slow models.
export const REQUEST_OPTS = {
  timeout: Number(process.env.MCP_TIMEOUT_MS || 180000),
};

/** Print a bordered title, matching the Week 4 demo style. */
export function printHeader(title) {
  console.log(BORDER);
  console.log(`  ${title}`);
  console.log(BORDER);
}

/**
 * Pause so the learner can predict before the reveal.
 * No-op when stdin is not a TTY (CI / piped runs).
 */
export async function pause(prompt = "  ⏸  Press Enter to continue… ") {
  if (!process.stdin.isTTY) return;
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  await new Promise((resolve) => rl.question(prompt, resolve));
  rl.close();
}

/** Print an error the way the protocol surfaces it to a client. */
export function printError(error) {
  const msg = String(error?.message ?? error);
  const key = error?.constructor?.name || "Error";
  console.log(`  [OUTPUT] ← ❌ [${key}] ${msg.slice(0, 120)}`);
  console.log();
}

/** Recursively print the leaf exceptions inside an AggregateError. */
export function printLeafExceptions(exc, indent = "  ") {
  if (exc && Array.isArray(exc.errors)) {
    for (const sub of exc.errors) printLeafExceptions(sub, indent + "  ");
  } else {
    console.log(`${indent}❌ ${exc?.constructor?.name || "Error"}: ${exc?.message ?? exc}`);
  }
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
