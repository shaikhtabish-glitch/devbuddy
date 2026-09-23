/**
 * Shared helpers for the Week 4 tool-calling demos (Node.js).
 */
import readline from "node:readline";

export const BORDER = "=".repeat(70);

/** Print a bordered title, matching the demo style. */
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
