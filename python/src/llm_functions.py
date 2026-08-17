"""
Week 2 — Structured output functions (the "action" that fills the contract).

These functions call the LLM and return typed objects. They live here — not in
schemas.py — so schemas.py stays pure (models only, no LLM imports). The schema
is the contract; these functions produce a model response that fits it.
"""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.schemas import BuildCheck, ServiceReadinessReport


def analyze_pr(
    title: str,
    diff: str,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> BuildCheck:
    """
    Analyze a PR and return a structured BuildCheck.

    Args:
        title: PR title
        diff: PR diff content
        temperature: 0.0 for deterministic output (default)
        max_tokens: Max tokens in the response. None = model default.

    Returns:
        BuildCheck with project, severity, summary, affected_files
    """
    llm = get_llm(temperature=temperature, max_tokens=max_tokens)
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


def generate_readiness_report(
    service_name: str,
    build_data: dict,
    deploy_data: dict,
    temperature: float = 0.0,
) -> ServiceReadinessReport:
    """
    Generate a ServiceReadinessReport from mock build/deploy data.

    This is the capstone pattern: take context (mock data standing in for
    RAG + tool output), feed it to the LLM, get back a typed, validated
    ServiceReadinessReport. No API calls to real services — just the LLM.

    Args:
        service_name: e.g. 'auth-service'
        build_data: dict with build status fields (status, last_deploy, failing_since)
        deploy_data: dict with deployment history (recent_deploys, active_incidents)
        temperature: 0.0 for deterministic output

    Returns:
        ServiceReadinessReport — composed, nested, validated
    """
    llm = get_llm(temperature=temperature)
    structured = llm.with_structured_output(ServiceReadinessReport)

    result = structured.invoke([
        SystemMessage(content=(
            "You are a site reliability engineer assessing whether a service is ready "
            "for its next release. You are given build health data and recent deployment "
            "history. Produce a ServiceReadinessReport.\n\n"
            "RULES:\n"
            "- If the build status is 'healthy' with no active incidents and recent "
            "deploys are all 'success', the service is ready with high confidence.\n"
            "- If the build is 'degraded' or there are active incidents, the service is "
            "NOT ready. List specific blockers.\n"
            "- If there is no data at all, set confidence to 'low'.\n"
            "- Every verdict must be supported by evidence. Reference the data you were given.\n"
            "- Blockers should be specific and actionable, not vague."
        )),
        HumanMessage(content=(
            f"Service: {service_name}\n\n"
            f"Build data:\n{json.dumps(build_data, indent=2)}\n\n"
            f"Deployment data:\n{json.dumps(deploy_data, indent=2)}"
        )),
    ])

    return result
