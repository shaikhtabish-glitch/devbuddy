"""
Demo 3: Inference Parameters — Temperature, Max Tokens, Cost

Same PR. Same Pydantic schema. Vary temperature, max_tokens.
Shows what changes and what stays the same.

Run: python scripts/week-02/demo-03-inference-parameters.py
"""
import os, sys, time, warnings
warnings.filterwarnings("ignore", message=".*Pydantic serializer.*")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.schemas import analyze_pr
from src.llm import get_llm

PR_TITLE = "Fix login redirect loop in auth-service"
PR_DIFF  = "Changed session validation in auth.py line 42-58. Expired tokens now return 401."

print("=" * 65)
print("  Demo 3: Inference Parameters — Temp, Max Tokens, Cost")
print("=" * 65)
print()
print(f"  INPUT: {PR_TITLE}")
print(f"         {PR_DIFF}")
print()

# ═══════════════════════════════════════════════════════════════
# Part 1: Temperature — content varies, contract holds
# ═══════════════════════════════════════════════════════════════
print("─" * 65)
print("  PART 1: Temperature — same input, 4 temperatures")
print("─" * 65)
print()

for temp in [0.0, 0.3, 0.7, 1.0]:
    label = "production" if temp == 0 else ("warm" if temp < 0.7 else "creative")
    result = analyze_pr(PR_TITLE, PR_DIFF, temperature=temp)
    print(f"  temp={temp} ({label}):")
    print(f"    severity={result.severity}")
    print(f"    summary=\"{result.summary[:70]}...\"")
    print()

print("  temp=0.0    → deterministic. Same output every time.")
print("  temp=0.7    → varies. Content drifts, fields remain valid.")
print("  temp=1.0    → creative. May flip severity or wording.")
print("  Key: Pydantic guarantees VALIDITY. Temperature controls CREATIVITY.")
print()

# ═══════════════════════════════════════════════════════════════
# Part 2: Max Tokens — truncation kills structured output
# ═══════════════════════════════════════════════════════════════
print("─" * 65)
print("  PART 2: Max Tokens — cost guard or truncation risk?")
print("─" * 65)
print()

for limit in [200, 50, 15, 8]:
    try:
        result = analyze_pr(PR_TITLE, PR_DIFF, temperature=0.0, max_tokens=limit)
        print(f"  max_tokens={limit:>3}: ✅ {result.severity}")
    except Exception as e:
        msg = str(e)[:80].replace("\n", " ")
        print(f"  max_tokens={limit:>3}: ❌ {msg}")

print()
print(f"  Set max_tokens=200 → safe. Cost ceiling: high.")
print(f"  Set max_tokens=8   → truncated. Validation fails.")
print(f"  Rule: max_tokens must fit your schema. Measure, don't guess.")
print()

# ═══════════════════════════════════════════════════════════════
# Part 3: Cost at different temperatures
# ═══════════════════════════════════════════════════════════════
print("─" * 65)
print("  PART 3: Cost — same task, different temperatures")
print("─" * 65)
print()

for temp in [0.0, 0.7]:
    llm = get_llm(temperature=temp)
    start = time.time()
    response = llm.invoke(f"PR: {PR_TITLE}\nDiff: {PR_DIFF}")
    elapsed = time.time() - start

    usage = response.usage_metadata or {}
    inp = usage.get("input_tokens", 0) if hasattr(usage, "get") else 0
    out = usage.get("output_tokens", 0) if hasattr(usage, "get") else 0
    cost = (inp * 0.15 + out * 0.60) / 1_000_000
    print(f"  temp={temp}: {inp}+{out} tokens, ~${cost:.6f}, {elapsed:.2f}s")

print()
print("  temp=0.0 vs temp=0.7 — cost is similar.")
print("  The architectural choice isn't about saving tokens here.")
print("  It's about deterministic contracts vs creative exploration.")
print()
print("=" * 65)
print("  Inference parameters are architectural decisions, not knobs.")
print("=" * 65)
