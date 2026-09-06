"""UC1 example: one student, whole paper -> one report.

    python examples/run_uc1.py

Runs offline in MOCK mode (SymPy verification is real). For live grading set
HOMOSAPIEN_LIVE=1 and configure AWS Bedrock.
"""
from homosapien import fixtures
from homosapien.workflows import run_uc1

report = run_uc1(fixtures.QUESTIONS, fixtures.NOTES, fixtures.single_student_answers())

print(f"{report.student_id}: {report.total_awarded}/{report.total_max}")
print(report.narrative)
for g in report.per_question:
    print(f"  {g.question_id}: {g.marks_awarded}/{g.max_marks}"
          + ("  [ESCALATED]" if g.escalate else ""))
