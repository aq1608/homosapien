"""UC2 example: many students -> per-student reports + cohort insights.

    python examples/run_uc2.py
"""
from homosapien import fixtures
from homosapien.workflows import run_uc2

reports, insights = run_uc2(
    fixtures.QUESTIONS, fixtures.NOTES, fixtures.cohort_answers()
)

for r in reports:
    print(f"{r.student_id}: {r.total_awarded}/{r.total_max} — {r.narrative}")

print("\nCohort insights:")
for ins in insights:
    print(f"  • {ins.observation}")
