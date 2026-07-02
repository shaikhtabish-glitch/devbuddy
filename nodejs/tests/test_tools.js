/**
 * Tests for src/tools.js — Week 4 (Node.js)
 */
import { describe, it, expect } from "vitest";
import {
  getBuildStatus,
  getRecentDeploys,
  getActiveIncidents,
  executeToolSafely,
  runToolLoop,
  runToolLoopWithTrace,
  ALL_TOOLS,
  TOOLS_BY_NAME,
} from "../src/tools.js";

// ═══════════════════════════════════════════════════════════════
// Tool definitions
// ═══════════════════════════════════════════════════════════════

describe("getBuildStatus", () => {
  it("returns status for a known service", async () => {
    const result = JSON.parse(
      await getBuildStatus.invoke({ service_name: "auth-service" })
    );
    expect(result.status).toBe("healthy");
    expect(result.last_deploy).toBeTruthy();
  });

  it("returns unknown for an unrecognized service", async () => {
    const result = JSON.parse(
      await getBuildStatus.invoke({ service_name: "nonexistent" })
    );
    expect(result.status).toBe("unknown");
    expect(result.error).toBeTruthy();
  });
});

describe("getRecentDeploys", () => {
  it("returns a list of deployment records", async () => {
    const result = JSON.parse(
      await getRecentDeploys.invoke({ service_name: "payment-api", limit: 3 })
    );
    expect(Array.isArray(result)).toBe(true);
    expect(result.length).toBe(3);
    expect(result[0].status).toBe("success");
  });

  it("returns empty list for service with no deploys", async () => {
    const result = JSON.parse(
      await getRecentDeploys.invoke({ service_name: "inventory-service" })
    );
    expect(result).toEqual([]);
  });
});

describe("getActiveIncidents", () => {
  it("returns active incidents for payment-api", async () => {
    const result = JSON.parse(
      await getActiveIncidents.invoke({ service_name: "payment-api" })
    );
    expect(result.length).toBe(1);
    expect(result[0].id).toBe("INC-842");
  });

  it("returns empty list for service with no incidents", async () => {
    const result = JSON.parse(
      await getActiveIncidents.invoke({ service_name: "auth-service" })
    );
    expect(result).toEqual([]);
  });
});

// ═══════════════════════════════════════════════════════════════
// Tool execution
// ═══════════════════════════════════════════════════════════════

describe("executeToolSafely", () => {
  it("executes a valid tool call successfully", async () => {
    const result = JSON.parse(
      await executeToolSafely({
        name: "get_build_status",
        args: { service_name: "auth-service" },
      })
    );
    expect(result.status).toBe("healthy");
  });

  it("returns structured error for unknown tool", async () => {
    const result = JSON.parse(
      await executeToolSafely({ name: "nonexistent_tool", args: {} })
    );
    expect(result.error).toBeTruthy();
    expect(result.available_tools).toBeTruthy();
  });
});

describe("ALL_TOOLS", () => {
  it("all tools have descriptions", () => {
    for (const t of ALL_TOOLS) {
      expect(t.description).toBeTruthy();
    }
  });

  it("TOOLS_BY_NAME maps all tools", () => {
    const names = ALL_TOOLS.map((t) => t.name).sort();
    expect(Object.keys(TOOLS_BY_NAME).sort()).toEqual(names);
  });
});

// ═══════════════════════════════════════════════════════════════
// Tool-calling loop (requires LLM)
// ═══════════════════════════════════════════════════════════════

describe("runToolLoop", () => {
  it("calls tool for build status question", async () => {
    const result = await runToolLoop(
      "Is the auth-service healthy?",
      0.0
    );
    expect(result.length).toBeGreaterThan(10);
    const lower = result.toLowerCase();
    expect(
      lower.includes("healthy") || lower.includes("auth")
    ).toBe(true);
  });

  it("answers directly when no tool needed", async () => {
    const result = await runToolLoop("What is 2 + 2?", 0.0);
    expect(result).toContain("4");
  });
});

describe("runToolLoopWithTrace", () => {
  it("returns a trace dict", async () => {
    const trace = await runToolLoopWithTrace(
      "Is the payment-api healthy?",
      0.0
    );
    expect(trace.answer).toBeTruthy();
    expect(trace.query).toBeTruthy();
    expect(trace.steps.length).toBeGreaterThanOrEqual(1);
  });

  it("works when no tools are called", async () => {
    const trace = await runToolLoopWithTrace("Hello!", 0.0);
    expect(trace.answer).toBeTruthy();
  });
});
