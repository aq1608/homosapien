"""UC1 — one student, whole paper -> one report."""
from __future__ import annotations

from ..schemas import MarkScheme, Notes, Question, StudentAnswer, StudentReport
from ..tools import grader, report_writer, scheme_builder


def run(
    questions: list[Question],
    notes: Notes,
    answers: list[StudentAnswer],
    provided_schemes: dict[str, MarkScheme] | None = None,
    *,
    auto_approve: bool = True,
) -> StudentReport:
    """Grade every question for a single student and write their report.

    ``auto_approve`` is a demo convenience; in production the educator approves
    each drafted scheme before grading runs.
    """
    provided_schemes = provided_schemes or {}
    students = {a.student_id for a in answers}
    if len(students) != 1:
        raise ValueError(f"UC1 expects exactly one student, got {len(students)}.")
    student_id = students.pop()

    by_qid = {a.question_id: a for a in answers}
    grades = []
    for q in questions:
        scheme = scheme_builder.build_or_load(q, notes, provided_schemes.get(q.id))
        if auto_approve and not scheme.approved:
            scheme_builder.approve(scheme)
        answer = by_qid.get(q.id)
        if answer is None:
            continue  # student didn't attempt this one
        grades.append(grader.grade_answer(q, scheme, answer))

    return report_writer.write_report(student_id, grades)
