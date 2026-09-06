"""Turn a student's per-question grades into their own narrative report."""
from __future__ import annotations

from ..llm import run_structured
from ..schemas import AnswerGrade, MarkLevel, StudentReport

_SYSTEM_PROMPT = """You write a short, encouraging-but-honest report to a
university mathematics student about one tutorial. Summarise how they did, name
the specific misconceptions behind lost marks, highlight genuine strengths, and
give 2-3 concrete next steps. Be specific to their working; never generic."""


def write_report(
    student_id: str, grades: list[AnswerGrade]
) -> StudentReport:
    total = sum(g.marks_awarded for g in grades)
    out_of = sum(g.max_marks for g in grades)

    def _mock() -> StudentReport:
        return _mock_report(student_id, grades, total, out_of)

    user = (
        f"STUDENT {student_id}. Grades (JSON):\n"
        + "\n".join(g.model_dump_json() for g in grades)
    )
    report = run_structured(_SYSTEM_PROMPT, user, StudentReport, _mock)
    # Trust our own arithmetic for the totals.
    report.student_id = student_id
    report.total_awarded = total
    report.total_max = out_of
    report.per_question = grades
    return report


def _mock_report(
    student_id: str, grades: list[AnswerGrade], total: int, out_of: int
) -> StudentReport:
    strengths, misconceptions = [], []
    for g in grades:
        for cg in g.criteria:
            if cg.level is MarkLevel.full and cg.criterion_id.upper().startswith("M"):
                strengths.append(f"{g.question_id}: sound method")
            if cg.level is not MarkLevel.full:
                misconceptions.append(f"{g.question_id}/{cg.criterion_id}: {cg.rationale}")
    escalated = [g.question_id for g in grades if g.escalate]
    narrative = (
        f"Scored {total}/{out_of}. "
        + ("Strong method throughout. " if strengths else "")
        + ("Lost marks were mainly on accuracy/steps noted below. " if misconceptions else "")
        + (f"Questions {', '.join(escalated)} need a human check before finalising."
           if escalated else "")
    )
    return StudentReport(
        student_id=student_id, total_awarded=total, total_max=out_of,
        per_question=grades, narrative=narrative.strip(),
        strengths=sorted(set(strengths)),
        misconceptions=misconceptions,
        next_steps=["Review the flagged steps", "Redo one similar problem"],
    )
