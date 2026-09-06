from homosapien.schemas import AnswerGrade
from homosapien.tools.transpose import (
    group_by_question,
    group_by_student,
    question_order,
)
from homosapien.fixtures import cohort_answers


def _grade(student, question):
    return AnswerGrade(
        student_id=student, question_id=question, criteria=[],
        marks_awarded=0, max_marks=4,
    )


def test_group_by_question_is_column_major():
    cols = group_by_question(cohort_answers())
    assert set(cols) == {"Q1", "Q2"}
    assert len(cols["Q1"]) == 3  # three students


def test_group_by_student_is_row_major():
    grades = [_grade("S1", "Q1"), _grade("S1", "Q2"), _grade("S2", "Q1")]
    rows = group_by_student(grades)
    assert len(rows["S1"]) == 2
    assert len(rows["S2"]) == 1


def test_question_order_stable():
    assert question_order(cohort_answers()) == ["Q1", "Q2"]
