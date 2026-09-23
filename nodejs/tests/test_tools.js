/**
 * Tests for src/tools.js — Week 4 (Node.js)
 */
import { describe, it, expect } from "vitest";
import { tool } from "@langchain/core/tools";
import { z } from "zod";
import {
  getBuildStatus,
  getRecentDeploys,
  getActiveIncidents,
  buildStatus,
  recentDeploys,
  activeIncidents,
  flaky,
  ConnectionError,
  executeToolSafely,
  runToolLoop,
  runToolLoopWithTrace,
  ALL_TOOLS,
  TOOLS_BY_NAME,
  MAX_TOOL_TURNS,
} from "../src/tools.js";

// ═══════════════════════════════════════════════════════════════
// Raw functions (the data sources)
// ═══════════════════════════════════════════════════════════════

describe("raw functions", () => {
  it("buildStatus returns data for a known service", () => {
    const result = JSON.parse(buildStatus("auth-service"));
    expect(result.status).toBe("healthy");
    expect(result.last_deploy).toBeTruthy();
  });

  it("buildStatus returns unknown for an unrecognized service", () => {
    const result = JSON.parse(buildStatus("nonexistent"));
    expect(result.status).toBe("unknown");
    expect(result.error).toBeTruthy();
  });

  it("recentDeploys respects the limit", () => {
    const result = JSON.parse(recentDeploys("payment-api", 2));
    expect(result.length).toBe(2);
  });

  it("activeIncidents returns an array", () => {
    expect(Array.isArray(JSON.parse(activeIncidents("auth-service")))).toBe(true);
  });
});

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
// Failure injection
// ═══════════════════════════════════════════════════════════════

describe("flaky", () => {
  it("fails the first N calls then succeeds", () => {
    const fn = flaky(buildStatus, 2);
    expect(() => fn("auth-service")).toThrow(ConnectionError);
    expect(() => fn("auth-service")).toThrow(ConnectionError);
    expect(JSON.parse(fn("auth-service")).status).toBe("healthy");
  });

  it("isolates counters between wrappers", () => {
    const a = flaky(buildStatus, 1);
    const b = flaky(buildStatus, 1);
    expect(() => a("auth-service")).toThrow(ConnectionError);
    // b's counter is untouched by a's failure
    expect(() => b("auth-service")).toThrow(ConnectionError);
    expect(JSON.parse(a("auth-service")).status).toBe("healthy");
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

  it("denies an unregistered tool via the registry whitelist", async () => {
    const registry = { get_build_status: {} }; // not even a real tool
    const result = JSON.parse(
      await executeToolSafely(
        { name: "delete_production_db", args: {} },
        0,
        { toolsByName: registry }
      )
    );
    expect(result.error).toBe("Unknown tool: 'delete_production_db'");
    expect(result.available_tools).toEqual(["get_build_status"]);
  });

  it("returns a structured error after retries are exhausted", async () => {
    const impl = flaky(buildStatus, 99);
    const flakyTool = tool(async ({ service_name }) => impl(service_name), {
      name: "get_build_status",
      description: "Return build status.",
      schema: z.object({ service_name: z.string() }),
    });

    const result = JSON.parse(
      await executeToolSafely(
        { name: "get_build_status", args: { service_name: "payment-api" } },
        1,
        { toolsByName: { get_build_status: flakyTool }, retryDelayMs: 0 }
      )
    );
    expect(result.status).toBe("failed");
    expect(result.attempts).toBe(2); // 1 initial + 1 retry
    expect(result.error).toBeTruthy();
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

  it("exposes a bounded tool-turn limit", () => {
    expect(MAX_TOOL_TURNS).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════
// Tool-calling loop (requires LLM)
// ═══════════════════════════════════════════════════════════════

describe("runToolLoop", () => {
  it("calls tool for build status question", async () => {
    const result = await runToolLoop("Is the auth-service healthy?", 0.0);
    expect(result.length).toBeGreaterThan(10);
    const lower = result.toLowerCase();
    expect(lower.includes("healthy") || lower.includes("auth")).toBe(true);
  }, 120_000);

  it("answers directly when no tool needed", async () => {
    const result = await runToolLoop("What is 2 + 2?", 0.0);
    expect(result).toContain("4");
  }, 120_000);
});

describe("runToolLoopWithTrace", () => {
  it("returns a trace with usage", async () => {
    const trace = await runToolLoopWithTrace("Is the payment-api healthy?", 0.0);
    expect(trace.answer).toBeTruthy();
    expect(trace.query).toBeTruthy();
    expect(trace.steps.length).toBeGreaterThanOrEqual(1);
    expect(trace.usage).toBeTruthy();
  }, 120_000);

  it("works when no tools are called", async () => {
    const trace = await runToolLoopWithTrace("Hello!", 0.0);
    expect(trace.answer).toBeTruthy();
  }, 120_000);
});
