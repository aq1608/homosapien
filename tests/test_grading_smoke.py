"""End-to-end smoke test of both workflows in MOCK mode (SymPy runs for real)."""
from homosapien import fixtures
from homosapien.schemas import MarkLevel
from homosapien.workflows import run_uc1, run_uc2


def test_uc1_produces_one_report_with_real_sympy_grade():
    report = run_uc1(
        fixtures.QUESTIONS, fixtures.NOTES, fixtures.single_student_answers()
    )
    assert report.student_id == "S1"
    # S1's correct integral must earn a SymPy-verified full accuracy mark.
    q1 = next(g for g in report.per_question if g.question_id == "Q1")
    a2 = next(cg for cg in q1.criteria if cg.criterion_id == "A2")
    assert a2.sympy_checked and a2.level is MarkLevel.full


def test_uc2_reports_per_student_and_flags_cohort():
    reports, insights = run_uc2(
        fixtures.QUESTIONS, fixtures.NOTES, fixtures.cohort_answers()
    )
    assert [r.student_id for r in reports] == ["S1", "S2", "S3"]
    # S2's wrong final answer loses the SymPy-gated accuracy mark.
    s2_q1 = next(g for r in reports if r.student_id == "S2"
                 for g in r.per_question if g.question_id == "Q1")
    a2 = next(cg for cg in s2_q1.criteria if cg.criterion_id == "A2")
    assert a2.sympy_checked and a2.level is MarkLevel.zero
    # S3's smudged scan must be escalated, not silently graded.
    s3_q1 = next(g for r in reports if r.student_id == "S3"
                 for g in r.per_question if g.question_id == "Q1")
    assert s3_q1.escalate
