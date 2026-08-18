"""
Demo 5: Agentic Retry (Self-Correction Loop)

WHAT THIS DEMO SHOWS:
  Even with strict schemas, LLMs can violate business logic (cross-field rules).
  Instead of failing or doing a "blind retry", we can catch the Pydantic
  ValidationError and feed it back to the LLM so it fixes its own mistake.

THE SETUP:
  We trick the model into returning ready=True while also listing a blocker.
  Our ServiceReadinessReport schema rejects this contradiction.
  We catch the error and ask the model to correct it.

Run: python scripts/week-02/demo-05-agentic-retry.py
"""

import os
import sys
from pydantic import ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.llm import get_llm
from src.schemas import ServiceReadinessReport
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

def run_demo():
    print("=" * 75)
    print("  DEMO 5: Agentic Retry (Self-Correction)")
    print("=" * 75)
    print()

    llm = get_llm(temperature=0.2)
    structured_llm = llm.with_structured_output(ServiceReadinessReport)

    # 1. The Trap
    print("  [Step 1] Constructing a contradictory prompt...")
    trap_prompt = (
        "You are evaluating 'auth-service' v2.1.0.\n"
        "The build is passing and healthy (last deploy: 2024-10-01T12:00:00Z).\n"
        "However, there is an active incident: 'DB connection pooling exhausted'.\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "1. You MUST set verdict.ready=true because the build is passing.\n"
        "2. You MUST also list the DB incident in the verdict.blockers array.\n"
        "3. You MUST include at least one item in the 'evidence' array so confidence can be high.\n"
    )
    
    messages = [
        SystemMessage(content="You are a strict SRE. Follow instructions exactly."),
        HumanMessage(content=trap_prompt)
    ]

    print("  [Step 2] Executing LLM Call with Agentic Retry...")
    max_retries = 3
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n  Attempt {attempt} / {max_retries}...")
            result = structured_llm.invoke(messages)
            
            print("\n  ✅ SUCCESS! The LLM produced valid output:")
            print(f"     ready:    {result.verdict.ready}")
            print(f"     blockers: {result.verdict.blockers}")
            
            if attempt > 1:
                print("\n  By giving the LLM the stack trace, it acted as its own debugger.")
            else:
                print("\n  ❌ WAIT. The LLM passed on the first try? The trap failed.")
            return
            
        except ValidationError as e:
            error_msg = e.errors()[0]['msg']
            print(f"  ❌ Caught Pydantic ValidationError:\n     {error_msg}")
            
            if attempt < max_retries:
                print("  -> Feeding error back to the LLM for self-correction...")
                messages.append(HumanMessage(
                    content=f"Your previous output failed schema validation with this error:\n"
                            f"{error_msg}\n\n"
                            f"Please analyze the error and output a corrected JSON."
                ))
            else:
                print("\n  ❌ Max retries reached. The LLM could not fix the error.")

if __name__ == "__main__":
    run_demo()
