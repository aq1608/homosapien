"""UC2 — many students -> grade column-major, report per student, + cohort insight."""
from __future__ import annotations

from ..schemas import (
    AnswerGrade,
    CohortInsight,
    MarkScheme,
    Notes,
    Question,
    StudentAnswer,
    StudentReport,
)
from ..tools import cohort_insights, grader, report_writer, scheme_builder
from ..tools.transpose import group_by_question, group_by_student


def run(
    questions: list[Question],
    notes: Notes,
    answers: list[StudentAnswer],
    provided_schemes: dict[str, MarkScheme] | None = None,
    *,
    auto_approve: bool = True,
) -> tuple[list[StudentReport], list[CohortInsight]]:
    """Return (one report per student, cohort insights).

    The key move: grade **column by column** (all students on one question) for a
    consistent bar, then **transpose** to write reports per student.
    """
    provided_schemes = provided_schemes or {}
    by_qid = {q.id: q for q in questions}
    columns = group_by_question(answers)

    all_grades: list[AnswerGrade] = []
    for qid, qanswers in columns.items():
        question = by_qid[qid]
        scheme = scheme_builder.build_or_load(
            question, notes, provided_schemes.get(qid)
        )
        if auto_approve and not scheme.approved:
            scheme_builder.approve(scheme)
        # Same approved scheme applied to every student on this question.
        for answer in qanswers:
            all_grades.append(grader.grade_answer(question, scheme, answer))

    # Transpose: column-major grades -> per-student reports.
    reports = [
        report_writer.write_report(student_id, grades)
        for student_id, grades in group_by_student(all_grades).items()
    ]
    reports.sort(key=lambda r: r.student_id)

    insights = cohort_insights.summarize(all_grades)
    return reports, insights
