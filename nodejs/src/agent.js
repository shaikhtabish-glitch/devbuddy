// Week 6 — Agent orchestrator: multi-step workflows
//
// This file will contain:
// - LangGraph state graph (or equivalent orchestrator)
// - Planning step (model decides step sequence at runtime)
// - Fixed chain (retrieve → tool → structured output)
// - Dynamic routing (model adapts to novel tasks)
// - Step guard (stop if > N steps or > $X cost)
//
// Imports:
//   import { getLlm } from "./llm.js"
//   import { BuildCheckSchema } from "./schemas.js"
//   import { retrieve } from "./rag.js"
//   import { getBuildStatus, getRecentDeploys } from "./tools.js"
//
// By the end of Week 6, this file orchestrates everything built so far.
