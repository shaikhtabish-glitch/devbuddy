/**
 * Demo 1: Start the MCP Server (SSE transport)
 *
 * Starts the DevBuddy MCP server on SSE transport (same as Python).
 * Connect with any MCP client at http://localhost:3001/sse
 *
 * Run: node scripts/week-05/demo-01-mcp-client.js
 */
console.error("Starting DevBuddy MCP Server (SSE transport)...");
console.error("Connect at: http://localhost:3001/sse");
console.error("");

import("../../src/mcp_server.js");
