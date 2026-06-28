"""
Week 2 — Validate a ServiceReadinessReport from mock data.

Loads one JSON scenario and validates it against the schema.
This is your starting point. Your self-learning assignment is below.

Run: python scripts/week-02/validate-readiness.py
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.schemas import ServiceReadinessReport

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "..", "shared", "data",
)

print("=" * 70)
print("  ServiceReadinessReport — Reference Validation")
print("=" * 70)
print()

# ── Reference: healthy scenario ───────────────────────────────
path = os.path.join(DATA_DIR, "service-readiness-healthy.json")
print(f"  Loading {path}...")

with open(path) as f:
    data = json.load(f)

report = ServiceReadinessReport.model_validate(data)
print(f"  ✅ Validated — {type(report).__name__}(")
print(f"       service.name   = {report.service.name}")
print(f"       service.version= {report.service.version}")
print(f"       build.status   = {report.build.status}")
print(f"       deploy.history = {len(report.deployment.recent_deploys)} deploys")
print(f"       verdict.ready  = {report.verdict.ready}")
print(f"       verdict.conf   = {report.verdict.confidence}")
print(f"       blockers       = {report.verdict.blockers}")
print(f"       evidence       = {len(report.evidence)} chunks")
print(f"     )")

print()
print("=" * 70)
print("  TAKE-HOME ASSIGNMENT")
print("=" * 70)
print()
print("  PART A — Load the other two scenarios:")
print("    1. Extend this script to also load and validate:")
print("       shared/data/service-readiness-degraded.json")
print("       shared/data/service-readiness-unknown.json")
print("    2. Add the same tests to tests/test_schemas.py")
print("       (follow the healthy example that's already there)")
print()
print("  PART B — LLM integration:")
print("    Use src.schemas.generate_readiness_report() to feed")
print("    the mock data to the LLM and get back a typed report.")
print("    Example:")
print()
print("      import json")
print("      from src.schemas import generate_readiness_report")
print()
print("      with open('../shared/data/service-readiness-healthy.json') as f:")
print("          data = json.load(f)")
print()
print("      report = generate_readiness_report(")
print("          service_name=data['service']['name'],")
print("          build_data=data['build'],")
print("          deploy_data=data['deployment'],")
print("          temperature=0.0,")
print("      )")
print()
print("      # report is a typed ServiceReadinessReport — no parsing needed!")
print("      print(report.model_dump_json(indent=2))")
print("      print(f'Cost: check OpenRouter dashboard')")
print()
print("    Run this for all 3 scenarios. Compare the LLM's verdict")
print("    to the hand-written JSON — does the model agree? Where")
print("    does it differ? What would you change in the prompt?")
print("=" * 70)
