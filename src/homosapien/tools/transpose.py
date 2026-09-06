"""The UC2 pivot: grade column-major, report row-major.

Grading one question across every student in a batch keeps the bar uniform
(consistency humans lose). Reporting is then organised per student — the output
the educator asked for. These helpers are the transpose between the two views.

Fully working, pure-Python code.
"""
from __future__ import annotations

from collections import defaultdict

from ..schemas import AnswerGrade, StudentAnswer


def group_by_question(
    answers: list[StudentAnswer],
) -> dict[str, list[StudentAnswer]]:
    """Column-major view: question_id -> that question's answers (all students)."""
    grouped: dict[str, list[StudentAnswer]] = defaultdict(list)
    for ans in answers:
        grouped[ans.question_id].append(ans)
    return dict(grouped)


def group_by_student(grades: list[AnswerGrade]) -> dict[str, list[AnswerGrade]]:
    """Row-major view: student_id -> that student's grades (all questions)."""
    grouped: dict[str, list[AnswerGrade]] = defaultdict(list)
    for grade in grades:
        grouped[grade.student_id].append(grade)
    return dict(grouped)


def question_order(answers: list[StudentAnswer]) -> list[str]:
    """Stable list of question ids in first-seen order."""
    seen: list[str] = []
    for ans in answers:
        if ans.question_id not in seen:
            seen.append(ans.question_id)
    return seen
