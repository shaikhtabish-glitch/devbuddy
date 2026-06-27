"""
DevBuddy Verification Script — Week 0

Verifies your environment is ready:
1. OpenRouter connectivity
2. Token usage + cost tracking
3. Python + dependencies working

Run: python src/verification.py
"""
import sys
import time
from datetime import datetime

# Ensure src/ is importable (Python 3.12+ doesn't auto-add CWD)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage
from src.llm import get_llm
from src.config import DEVBUDDY_MODEL


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

    questions = [
        "Say 'connected' in exactly one word.",
        "What is 2 + 2? Answer with just the number.",
        "Name one programming language in one word.",
    ]
    total_cost = 0.0
    total_tokens = 0

    for i, question in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] Asking: {question}")

        start = time.time()
        response = llm.invoke([HumanMessage(content=question)])
        elapsed = time.time() - start

        usage = response.usage_metadata or {}
        input_tokens = usage.get("input_tokens", 0) if hasattr(usage, "get") else 0
        output_tokens = usage.get("output_tokens", 0) if hasattr(usage, "get") else 0
        call_tokens = input_tokens + output_tokens
        total_tokens += call_tokens

        cost = (input_tokens * 0.15 + output_tokens * 0.60) / 1_000_000
        total_cost += cost

        print(f"  Response:    {response.content.strip()}")
        print(f"  Tokens:      {call_tokens} ({input_tokens} in / {output_tokens} out)")
        print(f"  Cost:        ${cost:.6f}")
        print(f"  Time:        {elapsed:.2f}s")
        print()

    print("=" * 60)
    print("  ✅ VERIFICATION PASSED")
    print(f"  Python:        {sys.version.split()[0]}")
    print(f"  Model:         {DEVBUDDY_MODEL}")
    print(f"  Total tokens:  {total_tokens}")
    print(f"  Total cost:    ${total_cost:.6f}")
    print(f"  Date:          {datetime.now().isoformat()}")
    print()
    print("  Your environment is ready for Week 1.")
    print("  Post this output to #devbuddy-series to confirm.")
    print()
    print("  What do you want DevBuddy to help you with?")
    print("  _______________________________________________")
    print("=" * 60)


if __name__ == "__main__":
    main()
