"""
DevBuddy Verification Script — Week 0

This script verifies:
1. OpenRouter connectivity
2. Structured output (LLM returns a typed object, not prose)
3. Cost tracking (token usage from OpenRouter)
4. Your environment is ready for Week 1

Run: python src/verification.py

This is NOT "Hello World." It's a microcosm of what DevBuddy becomes.
By Week 7, this pattern — LLM → structured output → cost tracking —
will be the foundation of a complete AI agent.
"""
import os
import sys
import time
from datetime import datetime

# Ensure src/ is importable (Python 3.12+ doesn't auto-add CWD)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from typing import Literal

from src.llm import get_llm
from src.config import DEVBUDDY_MODEL

# ─── Schema Definition ─────────────────────────────────────────
# This is a preview of Week 2. Today you just see it work.
class BuildCheck(BaseModel):
    """A build status check — the kind DevBuddy will generate autonomously by Week 6."""
    project: str = Field(description="Project name")
    status: Literal["passing", "failing", "in_progress", "unknown"] = Field(
        description="Build status"
    )
    confidence: float = Field(
        description="Confidence score 0-1. Must be ≤ 1 because this is a DEMO "
                    "with no real CI connection.",
        ge=0.0,
        le=1.0,
    )
    explanation: str = Field(description="One sentence explaining the result")


# ─── Execution ─────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  DevBuddy Verification — Week 0")
    print("=" * 60)
    print()

    try:
        llm = get_llm(temperature=0.0)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # include_raw=True → returns {"raw": AIMessage, "parsed": BuildCheck}
    structured_llm = llm.with_structured_output(BuildCheck, include_raw=True)

    projects = ["auth-service", "api-gateway", "user-service"]
    total_cost = 0.0
    total_tokens = 0

    for i, project in enumerate(projects, 1):
        print(f"[{i}/{len(projects)}] Checking: {project}...")

        start = time.time()

        result = structured_llm.invoke([
            SystemMessage(content=(
                "You are a build status checker. "
                "You are being evaluated on your ability to return valid, typed JSON. "
                "Be honest: you don't have real CI access, so set confidence appropriately. "
                "Explain WHY you picked the status you did."
            )),
            HumanMessage(content=(
                f"Check the build status of '{project}'.\n"
                f"Return a BuildCheck with:\n"
                f"- project: exactly '{project}'\n"
                f"- status: one of passing/failing/in_progress/unknown\n"
                f"- confidence: 0-1 (be honest — you don't have real CI access)\n"
                f"- explanation: one sentence"
            )),
        ])

        elapsed = time.time() - start

        # Unpack: parsed = typed object, raw = AIMessage with token metadata
        parsed = result["parsed"]
        raw_message = result["raw"]

        # Extract token usage from the raw LangChain message
        usage = raw_message.response_metadata.get("token_usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        call_tokens = prompt_tokens + completion_tokens
        total_tokens += call_tokens

        # Cost estimate (GPT-4o-mini via OpenRouter: ~$0.15/M input, ~$0.60/M output)
        cost = (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000
        total_cost += cost

        print(f"  Status:      {parsed.status}")
        print(f"  Confidence:  {parsed.confidence:.0%}")
        print(f"  Reason:      {parsed.explanation}")
        print(f"  Tokens:      {call_tokens} ({prompt_tokens} in / {completion_tokens} out)")
        print(f"  Cost:        ${cost:.6f}")
        print(f"  Time:        {elapsed:.2f}s")
        print(f"  Type:        {type(parsed).__name__} ← typed object, not a string!")
        print()

    # ─── Summary ───────────────────────────────────────────────
    print("=" * 60)
    print("  ✅ VERIFICATION PASSED")
    print(f"  Python:     {sys.version.split()[0]}")
    print(f"  Model:      {DEVBUDDY_MODEL}")
    print(f"  Total tokens: {total_tokens}")
    print(f"  Total cost:   ${total_cost:.6f}")
    print(f"  Date:       {datetime.now().isoformat()}")
    print()
    print("  Your environment is ready for Week 1.")
    print("  Post this output to #devbuddy-series to confirm.")
    print()
    print("  What do you want DevBuddy to help you with?")
    print("  _______________________________________________")
    print("=" * 60)


if __name__ == "__main__":
    main()
