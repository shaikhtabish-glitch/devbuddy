/**
 * Demo 1: Start the MCP Server
 *
 * Starts the DevBuddy MCP server on stdio transport.
 * Use the MCP Inspector to connect and test tools:
 *   npx @modelcontextprotocol/inspector node scripts/week-05/demo-01-mcp-client.js
 *
 * Run: node scripts/week-05/demo-01-mcp-client.js
 */
console.error("Starting DevBuddy MCP Server...");
console.error("Use MCP Inspector to connect: npx @modelcontextprotocol/inspector node scripts/week-05/demo-01-mcp-client.js");
console.error("");

// Import and run the MCP server
import "../src/mcp_server.js";
