/**
 * Demo 4: Full Tool Loop with Trace — all 3 tools, step-by-step, with cost
 *
 * THE POINT OF THIS DEMO: every tool call is a decision you can replay and
 * a bill you can read. If you cannot trace it, do not ship it. The trace is
 * your audit log — who was asked, what ran, what it returned, what it cost.
 *
 * Run: node scripts/week-04/demo-04-full-trace.js
 */
import readline from "readline/promises";
import { stdin as input, stdout as output } from "process";
import { MAX_TOOL_TURNS, runToolLoopWithTrace } from "../../src/tools.js";

const BORDER = "=".repeat(70);

async function pause(msg = "  ⏸  Press Enter to continue… ") {
  if (!process.stdin.isTTY) return;
  const rl = readline.createInterface({ input, output });
  await rl.question(msg);
  rl.close();
}

console.log(BORDER);
console.log("  Demo 4: Full Tool Loop — Trace, Audit, and Cost");
console.log(BORDER);
console.log();
console.log("  The trace is the audit log: who decided, what executed, what it");
console.log("  returned — and how many tokens each decision cost.");
console.log();

const queries = [
  "Is the auth-service healthy?",
  "What were the last 2 deployments for payment-api?",
  "Is payment-api healthy, what was deployed recently, and are there active incidents?",
];

console.log("  ⏸  PAUSE & PREDICT: for the last question — how many LLM calls");
console.log("     do you expect it to take? Guess, then continue.");
await pause();
console.log();

const grand = { input_tokens: 0, output_tokens: 0, total_tokens: 0, calls: 0 };

for (const query of queries) {
  console.log(`  QUERY: ${query}`);
  const trace = await runToolLoopWithTrace(query);
  console.log();

  for (const step of trace.steps) {
    if (step.type === "decide") {
      const t = step.tokens || {};
      console.log(`    [DECIDE]   in=${String(t.input_tokens || 0).padStart(5)} out=${String(t.output_tokens || 0).padStart(4)} tok`);
      console.log(`              ${step.content}`);
    } else if (step.type === "execute") {
      console.log(`    [EXECUTE]  ${step.tool}`);
      try {
        console.log(`              → ${JSON.stringify(JSON.parse(step.result)).slice(0, 130)}`);
      } catch {
        console.log(`              → ${step.result}`);
      }
    } else if (step.type === "answer") {
      const t = step.tokens || {};
      console.log(`    [ANSWER]   in=${String(t.input_tokens || 0).padStart(5)} out=${String(t.output_tokens || 0).padStart(4)} tok`);
      console.log(`              ${step.content}`);
    }
  }

  const calls = trace.steps.filter((s) => s.tokens).length;
  const u = trace.usage;
  console.log();
  console.log(
    `    → ${calls} LLM call(s);  ${u.input_tokens.toLocaleString()} in / ` +
      `${u.output_tokens.toLocaleString()} out / ${u.total_tokens.toLocaleString()} total tokens`
  );
  console.log();
  grand.input_tokens += u.input_tokens;
  grand.output_tokens += u.output_tokens;
  grand.total_tokens += u.total_tokens;
  grand.calls += calls;
}

console.log(BORDER);
console.log("  THE MESSAGE: the trace is your audit log. If you cannot trace a");
console.log("  decision — replay who decided, what executed, what it returned —");
console.log("  you should not ship it. And because each round is another LLM");
console.log("  call, the loop is bounded: a model that never stops calling tools");
console.log("  is a cost event, not a feature.");
console.log();
console.log(`  This run: ${grand.calls} LLM calls, ${grand.total_tokens.toLocaleString()} total tokens.`);
console.log(`  The loop is capped at MAX_TOOL_TURNS=${MAX_TOOL_TURNS} per query.`);
console.log();
console.log("  YOUR TURN:");
console.log("    • Multiply the total tokens by your model's per-token price and see");
console.log("      what one chained answer costs at scale (1,000 users × this).");
console.log("    • Raise a query whose answer needs NO tool and compare the bill.");
console.log(BORDER);
