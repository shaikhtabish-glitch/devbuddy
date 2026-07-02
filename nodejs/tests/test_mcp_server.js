/**
 * Tests for src/mcp_server.js — Week 5 (Node.js)
 */
import { describe, it, expect, beforeAll } from "vitest";

describe("MCP Server", () => {
  it("can be imported without errors", async () => {
    const mod = await import("../src/mcp_server.js");
    expect(mod).toBeTruthy();
  });
});
