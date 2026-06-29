# From One-Off Tools to Shared Infrastructure

> Pre-reading for Week 5. 5 minutes.

---

## The Problem

Week 4 gave DevBuddy tools. Powerful. But what happens when the next team needs `get_build_status`? They write it again. Different format. Different error handling. Now you have 5 copies of the same tool in 5 different codebases.

This is the **new copy-paste anti-pattern.** Every team wires the same tools differently. No discoverability. No shared error handling. No single source of truth.

---

## The Solution: MCP

**M**odel **C**ontext **P**rotocol. An open standard for model-tool communication.

```
┌──────────────────┐     ┌──────────────────┐     ┌─────┐
│   MCP Server     │ ←── │   MCP Client     │ ←── │ LLM │
│  (your tools)    │     │  (DevBuddy)      │     │     │
└──────────────────┘     └──────────────────┘     └─────┘
```

- **Server:** Holds the tools. Runs your internal logic. Exposes them over a transport (stdio for local dev, HTTP/SSE for production).
- **Client:** Connects to the server. Discovers available tools (`list_tools()`). Routes model tool-calls to the server.
- **Protocol:** Standard JSON-RPC messages over the transport. Any language. Any platform.

**Write once, consume anywhere.** Python, Node.js, Java — any MCP client can use your tools.

---

## The Architecture Decision

| Use MCP when | Use plain REST/HTTP when |
|---|---|
| Multiple teams need the same tools | One team, one tool, no sharing |
| You want tool discovery (client asks "what tools are available?") | You know exactly which endpoint to call |
| You want to swap providers without changing tools | Provider is locked, tool set is static |
| You're building an org-wide tool ecosystem | You're building a single-purpose integration |

---

## Transport Basics

| Transport | Use case | How |
|-----------|----------|-----|
| **stdio** | Local development. Server and client on the same machine. | Client spawns server as a subprocess. |
| **HTTP/SSE** | Production. Server runs remotely, multiple clients connect. | Server listens on a port, clients connect over HTTP. |

Today we use stdio — simple, no network config needed. Week 7 and beyond: HTTP for production.

---

## Security: Before You Expose a Tool

Ask these questions before putting an MCP server in front of real users:

- **Is this tool read-only?** If it can modify data, what's the blast radius?
- **Who can call it?** Authentication? API keys? IP allowlisting?
- **What's rate-limited?** Can a runaway agent call your tool 10,000 times?
- **What's logged?** Can you audit every tool call back to the user who triggered it?

Start with read-only tools. Add write tools only after auth and audit are in place.

---

## One Question to Hold

If your org had a single MCP server exposing build status, deployments, incidents, and docs, every team's DevBuddy would be 10x more capable. Which tool would you register first?
