/**
 * Tests for src/agent.js — Week 6 (Node.js)
 *
 * Two tiers:
 *   - unit: graph compilation + the budget guard (no services needed)
 *   - integration: skipped cleanly when the Node MCP server (:3001)
 *     or Qdrant (:6333) are not reachable.
 *
 * Scope note: the Node agent is the original string-typed design (see
 * docs/week-06.md → Scope: languages). These tests verify what it
 * actually is — not the Python reference's typed contracts.
 */
import { describe, it, expect } from "vitest";
import net from "net";

import {
  buildFixedChain,
  buildDynamicAgent,
  runFixedChain,
  runDynamicAgent,
  guard,
  MAX_STEPS,
  MAX_COST,
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

describe("graph compilation", () => {
  it("fixed chain compiles", () => {
    const agent = buildFixedChain();
    expect(agent).toBeTruthy();
    expect(typeof agent.invoke).toBe("function");
  });

  it("dynamic agent compiles", () => {
    const agent = buildDynamicAgent();
    expect(agent).toBeTruthy();
    expect(typeof agent.invoke).toBe("function");
  });
});

describe("budget guard", () => {
  it("trips at MAX_STEPS without calling the LLM", async () => {
    const decision = await guard({
      query: "x", steps: MAX_STEPS, cost: 0,
      service_name: "", context: "", build_status: "",
      deploys: "", incidents: "", report: "",
    });
    expect(decision).toBe("done");
  });

  it("trips at MAX_COST without calling the LLM", async () => {
    const decision = await guard({
      query: "x", steps: 0, cost: MAX_COST,
      service_name: "", context: "", build_status: "",
      deploys: "", incidents: "", report: "",
    });
    expect(decision).toBe("done");
  });
});

describe.skipIf(!SERVICES_UP)("integration (MCP :3001 + Qdrant :6333)", () => {
  it("fixed chain runs end-to-end and produces a report", async () => {
    const result = await runFixedChain("Is the payment-api ready for release?");
    expect(typeof result.report).toBe("string");
    expect(result.report.length).toBeGreaterThan(0);
    expect(result.steps).toBeGreaterThan(0);
    expect(result.cost).toBeGreaterThan(0);
  });

  it("dynamic agent runs and produces a report", async () => {
    const result = await runDynamicAgent("Is payment-api healthy?");
    expect(typeof result.report).toBe("string");
    expect(result.report.length).toBeGreaterThan(0);
    expect(result.steps).toBeGreaterThan(0);
  });
});