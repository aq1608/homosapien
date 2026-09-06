"""Sample data for the demos — a calculus question (SymPy-checkable) and a proof.

The computational question is wired so SymPy really distinguishes a correct
final answer from a wrong one:

    S1 final: exp(x)*(x-1)   -> equivalent to x*exp(x)-exp(x)  -> full accuracy
    S2 final: x*exp(x)+exp(x)-> NOT equivalent                 -> accuracy lost,
                                                                  method kept
"""
from __future__ import annotations

from .schemas import Notes, Question, QuestionType, StudentAnswer

NOTES = Notes(text=(
    "Integration by parts: ∫ u dv = u v − ∫ v du. Choose u by LIATE. "
    "For ∫ x e^x dx take u = x, dv = e^x dx, so du = dx, v = e^x. "
    "Proof by contradiction: assume the negation, derive a contradiction, conclude."
))

QUESTIONS = [
    Question(id="Q1", type=QuestionType.computational, max_marks=4,
             prompt="Evaluate ∫ x e^x dx."),
    Question(id="Q2", type=QuestionType.proof, max_marks=4,
             prompt="Prove that sqrt(2) is irrational."),
]


def single_student_answers() -> list[StudentAnswer]:
    """UC1: one student, both questions."""
    return [
        StudentAnswer(student_id="S1", question_id="Q1",
                      raw_text="u=x, dv=e^x dx; = x e^x - ∫ e^x dx",
                      final_expr="exp(x)*(x-1)"),
        StudentAnswer(student_id="S1", question_id="Q2",
                      raw_text="Assume sqrt(2)=a/b in lowest terms; 2b^2=a^2; a even; ..."),
    ]


def cohort_answers() -> list[StudentAnswer]:
    """UC2: three students across both questions."""
    return [
        # Q1
        StudentAnswer(student_id="S1", question_id="Q1",
                      raw_text="by parts", final_expr="exp(x)*(x-1)"),
        StudentAnswer(student_id="S2", question_id="Q1",
                      raw_text="by parts, sign slip", final_expr="x*exp(x)+exp(x)"),
        StudentAnswer(student_id="S3", question_id="Q1",
                      raw_text="by parts", final_expr="x*exp(x)-exp(x)",
                      transcription_confidence=0.6),  # smudged scan -> escalates
        # Q2
        StudentAnswer(student_id="S1", question_id="Q2",
                      raw_text="Assume a/b lowest terms; 2b^2=a^2; a even; b even; contradiction."),
        StudentAnswer(student_id="S2", question_id="Q2",
                      raw_text="Assume a/b; 2b^2=a^2; a even; stops."),
        StudentAnswer(student_id="S3", question_id="Q2",
                      raw_text="sqrt(2) is about 1.414 so not a fraction."),
    ]
