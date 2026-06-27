"""
Week 2 — Structured Outputs

Pydantic models + structured LLM calls.
The LLM returns typed objects, not prose.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from typing import Literal

from src.llm import get_llm


class BuildCheck(BaseModel):
    """A structured analysis of a PR or code change."""
    project: str = Field(description="Project or service name")
    severity: Literal["low", "medium", "high", "critical"] = Field(
        description="How urgent is this change?"
    )
    summary: str = Field(description="One-sentence summary of the change")
    affected_files: list[str] = Field(description="Files modified by this change")


def analyze_pr(title: str, diff: str, temperature: float = 0.0) -> BuildCheck:
    """
    Analyze a PR and return a structured BuildCheck.

    Args:
        title: PR title
        diff: PR diff content
        temperature: 0.0 for deterministic output (default)

    Returns:
        BuildCheck with project, severity, summary, affected_files
    """
    llm = get_llm(temperature=temperature)
    structured = llm.with_structured_output(BuildCheck)

    result = structured.invoke([
        SystemMessage(content=(
            "You are a code reviewer. Analyze the given PR and return a BuildCheck.\n"
            "- severity: 'critical' if it touches auth, payments, or security. "
            "'high' if it changes core logic. 'medium' for feature work. 'low' for docs/typos.\n"
            "- summary: one sentence describing what changed and why.\n"
            "- affected_files: list the files mentioned in the diff.\n"
            "- project: extract the project or service name from the PR context."
        )),
        HumanMessage(content=(
            f"PR Title: {title}\n\n"
            f"Diff:\n{diff}"
        )),
    ])

    return result
