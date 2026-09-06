"""Workflow detection and grader dispatch.

Two decisions, both cheap and deterministic:

1. *Which workflow?*  One student -> UC1 (one report). Many -> UC2 (grade
   column-major for consistency, report per student).
2. *Which grader?*  A question's ``type`` selects the computational (SymPy)
   path or the proof (logical-validity) path.
"""
from __future__ import annotations

from .schemas import QuestionType, Question, StudentAnswer


def detect_workflow(answers: list[StudentAnswer]) -> str:
    """Return ``"UC1"`` for a single student, ``"UC2"`` for many."""
    students = {a.student_id for a in answers}
    if not students:
        raise ValueError("No student answers supplied.")
    return "UC1" if len(students) == 1 else "UC2"


def dispatch_grader(question: Question) -> str:
    """Return the grader path name for a question."""
    return "proof" if question.type is QuestionType.proof else "computational"
