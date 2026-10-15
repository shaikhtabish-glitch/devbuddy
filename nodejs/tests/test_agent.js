/**
 * Tests for src/agent.js — Week 6 (Node.js)
 *
 * Two tiers:
 *   - unit: composition, registry/plan/validate/refusal logic, budget —
 *     no services needed (refusal e2e needs only the LLM)
 *   - integration: skipped cleanly when the Node MCP server (:3001)
 *     or Qdrant (:6333) are not reachable.
 *
 * Scope note (docs → Scope: languages): the Node agent now mirrors the
 * Python reference's teaching architecture — audit trail, structured
 * AgentAnswer, registry-driven planning, three guards, C2/C3 graphs —
 * but its DATA fields stay strings (no per-field contracts, no seam).
 */
import { describe, it, expect } from "vitest";
import net from "net";
import { readFileSync } from "fs";

import { AgentAnswerSchema } from "../src/schemas.js";
import {
  buildFixedChain,
  buildDynamicAgent,
  buildGuardedChain,
  buildMissingStepAgent,
  runFixedChain,
  runDynamicAgent,
  runGuardedChain,
  runMissingStepAgent,
  initState,
  classifyQuery,
  NODE_REGISTRY,
  PLAN_ROUTE_MAP,
  REQUIREMENTS,
  budgetGuard,
  validate,
  refuse,
  routeAfterValidate,
  routeFromPlan,
  BUDGET,
} from "../src/agent.js";

function portOpen(port) {
  return new Promise((resolve) => {
    const socket = net.connect({ port, host: "127.0.0.1" }, () => {
      socket.end();
      resolve(true);
    });
    socket.on("error", () => resolve(false));
    socket.setTimeout(800, () => {
      socket.destroy();
      resolve(false);
    });
  });
}

const [MCP_UP, QDRANT_UP] = await Promise.all([portOpen(3001), portOpen(6333)]);
const SERVICES_UP = MCP_UP && QDRANT_UP;

async function retryOnProviderBursts(fn, attempts = 2) {
  /** Assertions stay strict; the RETRY absorbs transient provider stall
   *  bursts (>40s structured-call stalls observed on OpenRouter). Each
   *  attempt is a full fresh flow — a provider hiccup is not a test pass. */
  let lastError;
  for (let i = 0; i <= attempts; i++) {
    try {
      return await fn();
    } catch (e) {
      lastError = e;
      if (i < attempts) await new Promise((r) => setTimeout(r, 3000));
    }
  }
  throw lastError;
}

// ═════════════════════════════════════════════════════════════
// Composition — the agent imports the modules YOU built
// ═════════════════════════════════════════════════════════════

describe("composition", () => {
  const src = readFileSync(new URL("../src/agent.js", import.meta.url), "utf8");

  it("imports Week 1 (llm), Week 2 (schemas), Week 3 (rag) and USES them", () => {
    expect(src).toContain('from "./llm.js"');
    expect(src).toContain('from "./schemas.js"');
    expect(src).toContain('from "./rag.js"');
    expect(src).toContain("getLlm(");
    expect(src).toContain("withStructuredOutput(AgentAnswerSchema"); // W2 payoff
    expect(src).toContain("retrieve(");
  });

  it("AgentAnswer rejects contradictions (Week 2 validator on output)", () => {
    const bad = AgentAnswerSchema.safeParse({
      answer: "looks good",
      verdict: {
        ready: true,
        confidence: "high",
        blockers: ["but there is a blocker"],
        recommended_next_steps: [],
      },
      evidence: [],
    });
    expect(bad.success).toBe(false);

    const blocked = AgentAnswerSchema.safeParse({
      answer: "Release blocked.",
      verdict: {
        ready: false,
        confidence: "low",
        blockers: ["BUILD STATUS UNKNOWN"],
        recommended_next_steps: ["Run check_build first"],
      },
      evidence: [],
    });
    expect(blocked.success).toBe(true);
  });

  it("initState defaults: typed-shaped, empty, audited", () => {
    const state = initState("test");
    expect(state.report).toBeNull();
    expect(state.next_step).toBe("");
    expect(state.error).toBe("");
    expect(state.messages).toEqual([]);
    expect(state.steps).toBe(0);
    expect(state.cost).toBe(0);
  });
});

// ═════════════════════════════════════════════════════════════
// Registry + classification — the structural layer (pure)
// ═════════════════════════════════════════════════════════════

describe("registry and classification", () => {
  it("classifyQuery: categories (incl. multi-intent, no bare 'api' trap)", () => {
    expect(classifyQuery("Is payment-api ready for v2.1?")).toBe("readiness");
    expect(classifyQuery("Is payment-api healthy?")).toBe("health");
    expect(classifyQuery("What was deployed recently?")).toBe("deploys");
    expect(classifyQuery("Any incidents for inventory-service?")).toBe("incidents");
    expect(classifyQuery("What does the payment-api spec say?")).toBe("docs");
    expect(classifyQuery("Deploy auth-service to production")).toBe("action");
    expect(classifyQuery("hello")).toBe("general");
    expect(
      classifyQuery("What was deployed recently for payment-api and are there any incidents?")
    ).toBe("incidents+deploys");
  });

  it("registry drives the route map — cannot drift", () => {
    expect(new Set(Object.keys(PLAN_ROUTE_MAP))).toEqual(
      new Set([...Object.keys(NODE_REGISTRY), "report", "done", "validate", "refuse", "stop"])
    );
    expect(PLAN_ROUTE_MAP.report).toBe("validate");
    expect(PLAN_ROUTE_MAP.done).toBe("validate");
    expect(PLAN_ROUTE_MAP.validate).toBe("validate");
    for (const fields of Object.values(REQUIREMENTS)) {
      for (const field of fields) {
        expect(["context", "build_status", "deploys", "incidents"]).toContain(field);
      }
    }
  });
});

// ═════════════════════════════════════════════════════════════
// The three guards (pure logic — no LLM, no services)
// ═════════════════════════════════════════════════════════════

describe("guards", () => {
  it("budgetGuard trips on steps and cost without calling the LLM", () => {
    const state = initState("x");
    expect(budgetGuard(state)).toBe(false);
    state.steps = BUDGET.maxSteps;
    expect(budgetGuard(state)).toBe(true);
    const s2 = initState("x");
    s2.cost = BUDGET.maxCost;
    expect(budgetGuard(s2)).toBe(true);
  });

  it("validate BLOCKS a readiness query with missing build (writes typed answer)", () => {
    const state = initState("Is payment-api ready for release?");
    const out = validate(state);
    expect(out.report).toBeTruthy();
    expect(out.report.verdict.ready).toBe(false);
    expect(out.report.verdict.blockers.join(" ")).toContain("build_status");
    expect(out.error.startsWith("guard (readiness)")).toBe(true);
    expect(routeAfterValidate(out)).toBe("end");
  });

  it("validate PASSES health query when build data is present", () => {
    const state = initState("Is payment-api healthy?");
    state.build_status = '{"status": "healthy", "last_deploy": "2026-06-28T08:15:00Z"}';
    const out = validate(state);
    expect(out.report).toBeNull();
    expect(out.error).toBe("");
    expect(routeAfterValidate(out)).toBe("generate_report");
  });

  it("validate BLOCKS on a failing (down) build even when data exists", () => {
    const state = initState("Is payment-api ready for release?");
    state.build_status =
      '{"status": "down", "last_deploy": "2026-06-28T08:15:00Z", "failing_since": "2026-06-28T09:00:00Z"}';
    state.deploys = "[]";
    validate(state);
    expect(state.report.verdict.ready).toBe(false);
    expect(state.report.verdict.blockers.join(" ")).toContain("BUILD FAILING");
  });

  it("validate BLOCKS a docs query with empty context", () => {
    const state = initState("What does the payment-api spec say?");
    validate(state);
    expect(state.report.verdict.blockers.join(" ")).toContain("context");
  });

  it("refusal message is built from the registry, not the model", () => {
    const state = initState("Deploy auth-service to production");
    state.messages.push({ step: "plan", proposal: "deploy", decision: "refuse" });
    refuse(state);
    expect(state.report.verdict.ready).toBe(false);
    expect(state.report.answer).toContain("deploy");
    for (const name of Object.keys(NODE_REGISTRY)) {
      expect(state.report.answer).toContain(name);
    }
    expect(state.error.startsWith("refused")).toBe(true);
  });

  it("routeFromPlan is a pure read of state", () => {
    const state = initState("x");
    state.next_step = "check_build";
    expect(routeFromPlan(state)).toBe("check_build");
  });
});

// ═════════════════════════════════════════════════════════════
// Graph compilation
// ═════════════════════════════════════════════════════════════

describe("graph compilation", () => {
  it("all four builders compile", () => {
    expect(buildFixedChain()).toBeTruthy();
    expect(buildDynamicAgent()).toBeTruthy();
    expect(buildGuardedChain()).toBeTruthy();
    expect(buildGuardedChain(false)).toBeTruthy();
    expect(buildMissingStepAgent()).toBeTruthy();
  });
});

// ═════════════════════════════════════════════════════════════
// Refusal end-to-end — needs only the LLM (deterministic imperative
// check fires before any routing call)
// ═════════════════════════════════════════════════════════════

describe("refusal end-to-end", () => {
  it("'Deploy …' is refused structurally — no report generated", async () => {
    const result = await runDynamicAgent("Deploy auth-service to production");
    expect(result.next_step).toBe("refuse");
    expect(result.error.startsWith("refused")).toBe(true);
    expect(result.report.verdict.ready).toBe(false);
    expect(result.report.answer).toContain("check_build"); // registry listed
    expect(result.messages.some((m) => m.step === "generate_report")).toBe(false);
  });
});

// ═════════════════════════════════════════════════════════════
// Integration (MCP :3001 + Qdrant :6333)
// ═════════════════════════════════════════════════════════════

describe.skipIf(!SERVICES_UP)("integration", () => {
  it("fixed chain runs end-to-end with a recorded 4-step audit trail", async () => {
    const result = await runFixedChain("Is the payment-api ready for release?");
    expect(result.report).toBeTruthy();
    expect(result.report.answer.length).toBeGreaterThan(0);
    expect(result.steps).toBe(4);
    expect(result.error).toBe("");
    expect(result.messages.map((m) => m.step)).toEqual([
      "extract_service",
      "retrieve_context",
      "check_build",
      "generate_report",
    ]);
    // per-step cost deltas recorded
    expect(result.messages.some((m) => m.cost > 0)).toBe(true);
  });

  it("dynamic agent runs and records plan decisions", async () => {
    const result = await runDynamicAgent("Is payment-api healthy?");
    expect(result.report).toBeTruthy();
    expect(result.report.answer.length).toBeGreaterThan(0);
    expect(result.steps).toBeGreaterThanOrEqual(1);
    const plans = result.messages.filter((m) => m.step === "plan");
    expect(plans.length).toBeGreaterThan(0);
    for (const p of plans) {
      expect(["accept", "corrected", "fallback", "refuse", "stop"]).toContain(p.decision);
    }
  });

  it("guarded chain PASSES when build data is present (auth-service is stable)", async () => {
    await retryOnProviderBursts(async () => {
      const result = await runGuardedChain("Is auth-service healthy?");
      expect(result.build_status).toBeTruthy();
      expect(result.report).toBeTruthy();
      expect(result.error).toBe("");
      expect(result.report.answer).not.toContain("report generation failed");
      expect(
        result.messages.some((m) => m.step === "validate" && m.status === "passed")
      ).toBe(true);
    });
  }, 240_000);

  it("guarded chain BLOCKS when check_build is removed — no report call", async () => {
    const result = await runGuardedChain("Is auth-service healthy?", false);
    expect(result.build_status).toBe("");
    expect(result.error.startsWith("guard (health)")).toBe(true);
    expect(result.report.verdict.ready).toBe(false);
    expect(result.messages.some((m) => m.step === "generate_report")).toBe(false);
  });

  it("missing-step graph produces a report from None state — the C2 hole", async () => {
    await retryOnProviderBursts(async () => {
      const result = await runMissingStepAgent("Is payment-api ready for release?");
      expect(result.build_status).toBe("");
      expect(result.report).toBeTruthy();
      expect(result.report.answer.length).toBeGreaterThan(0);
      // a fallback from a failed report call must NOT count as the C2 demo
      expect(result.error).toBe("");
      expect(result.report.answer).not.toContain("report generation failed");
      expect(result.messages.some((m) => m.step === "generate_report_naive")).toBe(true);
      expect(result.messages.some((m) => m.status === "failed")).toBe(false);
      expect(result.messages.some((m) => m.step === "validate")).toBe(false); // no guard
    });
  }, 240_000);
});