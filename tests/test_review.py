"""The educator HTML review sheet renders from graded output."""
from homosapien import fixtures
from homosapien.tools import review
from homosapien.workflows import run_uc2


def test_build_html_contains_students_and_marks():
    answers = fixtures.cohort_answers()
    reports, _ = run_uc2(fixtures.QUESTIONS, fixtures.NOTES, answers)
    html = review.build_html(reports, answers)

    assert html.lstrip().startswith("<!doctype html>")
    for sid in ("S1", "S2", "S3"):
        assert f'id="{sid}"' in html          # each student section present
    assert "Marks" in html                     # per-criterion block rendered
    assert "Transcript" in html                # transcript shown for typed answers


def test_build_html_flags_escalations():
    answers = fixtures.cohort_answers()          # S3 has a low-confidence scan
    reports, _ = run_uc2(fixtures.QUESTIONS, fixtures.NOTES, answers)
    html = review.build_html(reports, answers)
    assert "needs review" in html                # at least one escalation surfaced
