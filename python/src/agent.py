# Week 6 — Agent orchestrator: multi-step workflows
#
# This file will contain:
# - LangGraph state graph (or equivalent orchestrator)
# - Planning step (model decides step sequence at runtime)
# - Fixed chain (retrieve → tool → structured output)
# - Dynamic routing (model adapts to novel tasks)
# - Step guard (stop if > N steps or > $X cost)
#
# Imports:
#   from src.llm import get_llm
#   from src.schemas import BuildCheck
#   from src.rag import retrieve
#   from src.tools import get_build_status, get_recent_deploys
#
# By the end of Week 6, this file orchestrates everything built so far.
