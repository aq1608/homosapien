"""Cross-student patterns worth reteaching (UC2 only).

Because grading is column-major, the agent has already seen every student's
answer to each question — so shared errors are cheap to surface.
"""
from __future__ import annotations

from collections import defaultdict

from ..schemas import AnswerGrade, CohortInsight, MarkLevel

# Fraction of the cohort that must miss a criterion before it's flagged.
DEFAULT_THRESHOLD = 0.4


def summarize(
    grades: list[AnswerGrade], *, threshold: float = DEFAULT_THRESHOLD
) -> list[CohortInsight]:
    by_q: dict[str, list[AnswerGrade]] = defaultdict(list)
    for g in grades:
        by_q[g.question_id].append(g)

    insights: list[CohortInsight] = []
    for qid, qgrades in by_q.items():
        # criterion_id -> students who did not get it full
        missed: dict[str, list[str]] = defaultdict(list)
        for g in qgrades:
            for cg in g.criteria:
                if cg.level is not MarkLevel.full:
                    missed[cg.criterion_id].append(g.student_id)
        n = len(qgrades)
        for cid, students in missed.items():
            if n and len(students) / n >= threshold:
                insights.append(CohortInsight(
                    question_id=qid,
                    observation=(
                        f"{len(students)}/{n} students lost {cid} on {qid} "
                        "— worth reteaching."
                    ),
                    affected_students=sorted(students),
                ))
    return insights
