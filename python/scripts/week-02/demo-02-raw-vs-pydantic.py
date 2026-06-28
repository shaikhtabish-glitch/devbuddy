"""Demo 2: Raw JSON Prompting vs. Pydantic Structured Output

This script demonstrates why raw string prompting is a fragile 'request'
while Pydantic structured output acts as an unbreakable 'contract'.

We run both approaches at an elevated temperature (1.5) to simulate
the natural drift/chaos that happens under high temperature or complex schemas.
"""

import os
import sys
import json
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator

# Adjust path for local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.llm import get_llm
from langchain_core.messages import HumanMessage

# =====================================================================
# 1. SETUP THE DATA
# =====================================================================
diff_input = """Fix login redirect loop in auth-service (PROJ-421)
Changed session token validation in src/auth.py lines 42-58.
Previously expired tokens caused infinite redirect for 15% of users.
Now returns 401 with clear error. No DB changes. Rollback: revert commit.
Files: src/auth.py, tests/test_auth.py"""

# =====================================================================
# 2. DEFINING THE PYDANTIC SCHEMA ("THE CONTRACT")
# =====================================================================
class ChangeSchema(BaseModel):
    type: Literal["bug", "feature", "refactor", "hotfix"] = Field(
        description="The category of the change"
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(
        description="The impact severity level"
    )
    ticket: Optional[str] = Field(
        None, description="The ticket ID (e.g., PROJ-123) if present, else null"
    )

class DetailsSchema(BaseModel):
    summary: str = Field(description="A single sentence summary of the diff")
    root_cause: str = Field(description="The underlying issue that was fixed")
    user_impact_pct: Optional[int] = Field(
        None, description="The percentage of users impacted as a raw integer (e.g. 15)"
    )

    @field_validator("user_impact_pct", mode="before")
    @classmethod
    def clean_percentage(cls, v):
        """Coerces strings like '15%' or '15 percent' into an integer 15."""
        if isinstance(v, str):
            digits = "".join(filter(str.isdigit, v))
            return int(digits) if digits else None
        return v

class TechnicalSchema(BaseModel):
    files_changed: List[str] = Field(description="Exact file paths modified")
    db_changed: bool = Field(description="Whether database migrations are required")
    rollback: str = Field(description="Instructions on how to revert the changes")

class DiffAnalysis(BaseModel):
    """The root container schema representing the structured extraction."""
    change: ChangeSchema
    details: DetailsSchema
    technical: TechnicalSchema


# =====================================================================
# 3. RUNNING THE COMPARISON DEMO
# =====================================================================
def run_demo():
    print("=" * 70)
    print("  DEMO: Raw JSON Prompting (Request) vs. Pydantic (Contract)")
    print("=" * 70)
    print(f"Input Diff:\n{'-'*20}\n{diff_input}\n{'-'*20}\n")

    # A high temperature simulates real-world stress/complexity where LLM drift occurs
    test_temperature = 1.5
    print(f"Test Configuration: Temperature = {test_temperature} (High Chaos Mode)\n")

    # -----------------------------------------------------------------
    # APPROACH A: RAW PROMPTING ("The Request")
    # -----------------------------------------------------------------
    print("Approach A: Raw JSON Prompting")
    print("  -> Prompting the model to return JSON structure directly.")

    raw_prompt = """Analyze this code change and extract details. Return a JSON object matching this schema:
    {
      "change": { "type": "bug"|"feature", "severity": "low"|"high", "ticket": "string" },
      "details": { "summary": "string", "root_cause": "string", "user_impact_pct": integer },
      "technical": { "files_changed": ["string"], "db_changed": boolean, "rollback": "string" }
    }

    DIFF:
    """

    llm_raw = get_llm(temperature=test_temperature)

    try:
        response_raw = llm_raw.invoke([HumanMessage(content=f"{raw_prompt}\n{diff_input}")])
        raw_text = response_raw.content.strip()

        # Try parsing the raw text manually
        data = json.loads(raw_text)
        print("  ✅ Parse Success!")
        print(f"     Extracted keys: {list(data.keys())}")
        print(f"     User Impact Pct: {data.get('details', {}).get('user_impact_pct')} (Type: {type(data.get('details', {}).get('user_impact_pct')).__name__})")
    except json.JSONDecodeError:
        print("  ❌ JSONDecodeError: The model returned conversational wrapper or markdown backticks!")
        print(f"     Raw response snippet: {raw_text[:120].replace(chr(10), ' ')}...")
    except Exception as e:
        print(f"  ❌ Runtime Error ({type(e).__name__}): {str(e)}")

    print("\n" + "-"*50 + "\n")

    # -----------------------------------------------------------------
    # APPROACH B: PYDANTIC + STRUCTURED OUTPUT ("The Contract")
    # -----------------------------------------------------------------
    print("Approach B: Pydantic + with_structured_output()")
    print("  -> Constraining the model output using Schema/Tool bindings.")

    llm_structured = get_llm(temperature=test_temperature)
    # Bind the schema to the model using LangChain's built-in structured output mechanism
    structured_llm = llm_structured.with_structured_output(DiffAnalysis)

    try:
        # We only need to provide the raw input—no complex formatting instructions required!
        pydantic_result = structured_llm.invoke(f"Analyze this diff:\n{diff_input}")

        print("  ✅ Extraction Success!")
        print(f"     Pydantic Object: {pydantic_result}")
        print(f"     Validated User Impact Pct: {pydantic_result.details.user_impact_pct} (Type: {type(pydantic_result.details.user_impact_pct).__name__})")
        print("     (Note: '15%' was safely coerced into an integer 15 automatically!)")
    except Exception as e:
        print(f"  ❌ Pydantic Extraction Failed: {str(e)}")

    print("\n" + "=" * 70)
    print("  Takeaways:")
    print("  1. Raw JSON: Relies on the model's 'good behavior' at generation time.")
    print("               Under high temperature, it easily breaks due to markdown/text.")
    print("  2. Pydantic: Forces the API to conform to the schema at the token level.")
    print("               Also guarantees type safety (automatic '15%' -> 15 conversion).")
    print("=" * 70)

if __name__ == "__main__":
    run_demo()
