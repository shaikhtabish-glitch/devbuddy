"""
Week 2 — Validate a ServiceReadinessReport from mock data.

Loads three JSON scenarios, validates each against the schema,
and reports pass/fail with the validated typed objects.

No API calls. Pure Pydantic. Instant feedback.

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

SCENARIOS = [
    ("Healthy", "service-readiness-healthy.json"),
    ("Degraded", "service-readiness-degraded.json"),
    ("Unknown", "service-readiness-unknown.json"),
]

print("=" * 70)
print("  ServiceReadinessReport — Mock Data Validation")
print("=" * 70)
print()

for label, filename in SCENARIOS:
    path = os.path.join(DATA_DIR, filename)
    print(f"  [{label}] Loading {filename}...")

    with open(path) as f:
        data = json.load(f)

    try:
        report = ServiceReadinessReport.model_validate(data)
        print(f"    ✅ Validated — {type(report).__name__}(")
        print(f"         service.name   = {report.service.name}")
        print(f"         service.version= {report.service.version}")
        print(f"         build.status   = {report.build.status}")
        print(f"         deploy.history = {len(report.deployment.recent_deploys)} deploys")
        print(f"         verdict.ready  = {report.verdict.ready}")
        print(f"         verdict.conf   = {report.verdict.confidence}")
        print(f"         blockers       = {report.verdict.blockers}")
        print(f"         evidence       = {len(report.evidence)} chunks")
        print(f"       )")
    except Exception as e:
        print(f"    ❌ Validation failed: {e}")

    print()

print("=" * 70)
print("  These three scenarios exercise:")
print("    • Nested model composition")
print("    • Optional fields (failing_since, relevance_score)")
print("    • field_validator (failing_since required when degraded)")
print("    • model_validator (ready=True + blockers=[] contradiction)")
print("    • model_validator (no evidence → confidence must be 'low')")
print("=" * 70)
