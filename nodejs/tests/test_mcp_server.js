/**
 * Tests for src/mcp_server.js — Week 5 (Node.js)
 *
 * Uses the MCP SDK's in-memory transport to exercise the real protocol
 * (tools, resources, prompts) without binding a network port.
 */
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import {
  createServer,
  TOOL_DEFINITIONS,
  PROMPT_DEFINITIONS,
  listSharedResources,
  listSharedResourceTemplates,
  readSharedResource,
  getIncidentAnalysisPrompt,
  checkRateLimit,
  resetRateLimits,
} from "../src/mcp_server.js";

describe("MCP server definitions", () => {
  it("registers all tools, including the destructive one", () => {
    const names = TOOL_DEFINITIONS.map((t) => t.name);
    expect(names).toContain("get_build_status");
    expect(names).toContain("get_recent_deploys");
    expect(names).toContain("get_active_incidents");
    expect(names).toContain("delete_incident_record");
  });

  it("exposes a resource template but no static resources", () => {
    expect(listSharedResources()).toEqual([]);
    const templates = listSharedResourceTemplates();
    expect(templates.length).toBe(1);
    expect(templates[0].uriTemplate).toBe("file://shared/data/{filename}");
  });

  it("reads a shared document", () => {
    const doc = readSharedResource("file://shared/data/inventory-service-sla.md");
    expect(doc.text.length).toBeGreaterThan(0);
    expect(doc.mimeType).toBe("text/markdown");
  });

  it("rejects paths outside shared/data", () => {
    expect(() => readSharedResource("file:///etc/passwd")).toThrow(/Resource not found/);
    expect(() =>
      readSharedResource("file://shared/data/../../etc/passwd")
    ).toThrow(/Resource not found/);
  });

  it("defines the incident analysis prompt", () => {
    expect(PROMPT_DEFINITIONS[0].name).toBe("incident_analysis_prompt");
    const prompt = getIncidentAnalysisPrompt("auth-service");
    expect(prompt.messages[0].content.text).toContain("auth-service");
  });

  it("rate limits a tool after the limit is exceeded", () => {
    resetRateLimits();
    expect(() => {
      checkRateLimit("test_tool", 3, 30);
      checkRateLimit("test_tool", 3, 30);
      checkRateLimit("test_tool", 3, 30);
    }).not.toThrow();
    expect(() => checkRateLimit("test_tool", 3, 30)).toThrow(/RateLimitExceeded/);
    resetRateLimits();
  });
});

describe("MCP server over in-memory transport", () => {
  let client;
  let server;

  beforeAll(async () => {
    server = createServer();
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    client = new Client(
      { name: "test-client", version: "1.0.0" },
      { capabilities: {} }
    );
    await Promise.all([
      server.connect(serverTransport),
      client.connect(clientTransport),
    ]);
  });

  afterAll(async () => {
    await client?.close().catch(() => {});
    await server?.close().catch(() => {});
  });

  it("lists the four tools over the wire", async () => {
    const { tools } = await client.listTools();
    expect(tools.map((t) => t.name)).toContain("delete_incident_record");
  });

  it("lists the resource template over the wire", async () => {
    const { resourceTemplates } = await client.listResourceTemplates();
    expect(resourceTemplates[0].uriTemplate).toBe("file://shared/data/{filename}");
  });

  it("reads a resource over the wire", async () => {
    const res = await client.readResource({
      uri: "file://shared/data/inventory-service-sla.md",
    });
    expect(res.contents[0].text).toContain("Inventory Service");
  });

  it("rejects a non-exposed resource over the wire", async () => {
    await expect(
      client.readResource({ uri: "file:///etc/passwd" })
    ).rejects.toThrow(/Resource not found/);
  });

  it("lists and fetches the prompt over the wire", async () => {
    const { prompts } = await client.listPrompts();
    expect(prompts.map((p) => p.name)).toContain("incident_analysis_prompt");

    const prompt = await client.getPrompt({
      name: "incident_analysis_prompt",
      arguments: { service_name: "payment-api" },
    });
    expect(prompt.messages[0].content.text).toContain("payment-api");
  });

  it("rejects an unauthorized destructive tool call", async () => {
    const res = await client.callTool({
      name: "delete_incident_record",
      arguments: { incident_id: "INC-123", admin_token: "none" },
    });
    const body = JSON.parse(res.content[0].text);
    expect(body.status).toBe("error");
    expect(body.reason).toMatch(/Unauthorized/);
  });

  it("allows an authorized destructive tool call", async () => {
    const res = await client.callTool({
      name: "delete_incident_record",
      arguments: { incident_id: "INC-123", admin_token: "super-secret-approval-123" },
    });
    const body = JSON.parse(res.content[0].text);
    expect(body.status).toBe("success");
    expect(body.deleted).toBe("INC-123");
  });
});
