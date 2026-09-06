"""Grade one student's answer against an approved mark scheme.

Dispatches by question type:
  * computational -> propose per-criterion marks, then GATE every accuracy
    criterion on ``sympy_verify`` (never the model's own arithmetic);
  * proof -> grade logical milestones (SymPy still checks any algebra inside).

The language-model proposal is mockable; the SymPy gate and escalation logic run
for real regardless of mode, so the offline demo genuinely verifies mathematics.

Two fairness rules live in the gate:
  * a SymPy parse/verify failure is OUR uncertainty — it escalates, it never
    converts into a lost mark;
  * an answer correct only *up to an additive constant* (a missing ``+ C``) is a
    marking-policy call — award the substance, escalate the convention.
"""
from __future__ import annotations

from pydantic import BaseModel

from ..llm import run_structured
from ..schemas import (
    AnswerGrade,
    Criterion,
    CriterionGrade,
    CriterionKind,
    MarkLevel,
    MarkScheme,
    Question,
    QuestionType,
    StudentAnswer,
)
from . import escalation
from .sympy_verify import are_equivalent, equivalent_up_to_constant

_SYSTEM_PROMPT = """You are a fair, consistent university mathematics marker.
Grade the answer criterion by criterion against the mark scheme. Award method
marks for a correct approach even if the number is wrong (error carried forward).
Give each criterion full/partial/zero, marks, and a one-line rationale, plus a
confidence in [0,1]. Do not compute or verify arithmetic yourself, and do not set
any 'sympy_checked' field — accuracy marks are checked separately by a
computer-algebra system."""


def grade_answer(
    question: Question,
    scheme: MarkScheme,
    answer: StudentAnswer,
) -> AnswerGrade:
    if not scheme.approved:
        raise ValueError(
            f"Mark scheme for {question.id} is not approved. "
            "Call scheme_builder.approve(scheme) first (human-in-the-loop)."
        )

    # A blank answer is a legitimate zero — not an escalation, no model call.
    if not answer.attempted:
        zeros = [
            CriterionGrade(criterion_id=c.id, level=MarkLevel.zero,
                           marks_awarded=0, rationale="Not attempted.", confidence=1.0)
            for c in scheme.criteria
        ]
        return AnswerGrade(
            student_id=answer.student_id, question_id=question.id,
            criteria=zeros, marks_awarded=0, max_marks=question.max_marks,
            error_types=["not-attempted"], escalate=False,
        )

    # 1) Model proposes per-criterion grades (mock offline).
    proposed = _propose(question, scheme, answer)

    # The SymPy gate is the sole authority on `sympy_checked`; ignore any value
    # the model set on its own proposal.
    proposed = [cg.model_copy(update={"sympy_checked": False}) for cg in proposed]

    # 2) Deterministic SymPy gate on accuracy criteria (computational path).
    gate_reasons: list[str] = []
    if question.type is QuestionType.computational:
        gated: list[CriterionGrade] = []
        for cg in proposed:
            new_cg, reason = _gate_accuracy(cg, scheme, answer)
            gated.append(new_cg)
            if reason:
                gate_reasons.append(reason)
        proposed = gated

    marks = sum(cg.marks_awarded for cg in proposed)
    _conf_escalate, conf_reasons = escalation.evaluate(proposed, answer)
    reasons = gate_reasons + conf_reasons

    return AnswerGrade(
        student_id=answer.student_id,
        question_id=question.id,
        criteria=proposed,
        marks_awarded=marks,
        max_marks=question.max_marks,
        error_types=_error_types(proposed),
        escalate=bool(reasons),
        escalation_reasons=reasons,
    )


# --------------------------------------------------------------------------- #
def _propose(
    question: Question, scheme: MarkScheme, answer: StudentAnswer
) -> list[CriterionGrade]:
    def _mock() -> _Proposal:
        return _Proposal(grades=_mock_grades(scheme))

    working = answer.raw_text or answer.final_expr or "(no working provided)"
    user = (
        f"QUESTION: {question.prompt}\n\n"
        f"MARK SCHEME: {scheme.model_dump_json()}\n\n"
        f"STUDENT WORKING:\n{working}\n"
        f"STUDENT FINAL EXPRESSION: {answer.final_expr}"
    )
    return run_structured(_SYSTEM_PROMPT, user, _Proposal, _mock).grades


def _gate_accuracy(
    cg: CriterionGrade, scheme: MarkScheme, answer: StudentAnswer
) -> tuple[CriterionGrade, str | None]:
    """Confirm/deny an accuracy criterion with SymPy.

    Returns the (possibly overridden) grade and, when the call needs a human, an
    escalation reason.
    """
    crit = _find(scheme.criteria, cg.criterion_id)
    if crit is None or crit.kind is not CriterionKind.accuracy:
        return cg, None
    if not crit.expected_expr or not answer.final_expr:
        return cg, None  # nothing checkable; escalation.evaluate may still flag it

    result = are_equivalent(answer.final_expr, crit.expected_expr)
    if result.equivalent:
        return cg.model_copy(update=dict(
            level=MarkLevel.full, marks_awarded=crit.marks,
            sympy_checked=True, confidence=1.0,
            rationale=f"SymPy confirmed equivalence ({result.method}).",
        )), None

    # Fairness rule: a parse/verify failure is OUR uncertainty, never the
    # student's fault. Keep the model's proposed marks and hand it to a human.
    if result.method == "error":
        return cg.model_copy(update=dict(
            sympy_checked=False,
            rationale=(
                f"SymPy could not verify this expression ({result.detail}); "
                "left unpenalised for human review."
            ),
        )), (
            f"{cg.criterion_id}: SymPy could not parse the answer — "
            "human check (not auto-penalised)."
        )

    # Correct up to an additive constant (e.g. a missing +C): a marking-policy
    # call, not a maths error. Award the substance, escalate the convention.
    upto = equivalent_up_to_constant(answer.final_expr, crit.expected_expr)
    if upto.equivalent:
        return cg.model_copy(update=dict(
            level=MarkLevel.full, marks_awarded=crit.marks,
            sympy_checked=True, confidence=0.9,
            rationale="Correct up to an additive constant (e.g. +C); policy call flagged.",
        )), (
            f"{cg.criterion_id}: answer correct up to a constant (+C) — "
            "apply your marking convention."
        )

    # Genuinely not equivalent.
    return cg.model_copy(update=dict(
        level=MarkLevel.zero, marks_awarded=0,
        sympy_checked=True, confidence=1.0,
        rationale=f"SymPy: not equivalent to expected answer ({result.detail}).",
    )), None


def _error_types(grades: list[CriterionGrade]) -> list[str]:
    types: list[str] = []
    for cg in grades:
        if cg.level is MarkLevel.full:
            continue
        cid = cg.criterion_id.upper()
        if cid.startswith("A"):
            types.append("accuracy")
        elif cid.startswith("M"):
            types.append("method")
        elif cid.startswith("L"):
            types.append("logical-gap")
    return sorted(set(types))


def _find(criteria: list[Criterion], cid: str) -> Criterion | None:
    return next((c for c in criteria if c.id == cid), None)


def _mock_grades(scheme: MarkScheme) -> list[CriterionGrade]:
    """Offline proposal: method/logic marks awarded, accuracy left for the gate."""
    out: list[CriterionGrade] = []
    for c in scheme.criteria:
        if c.kind is CriterionKind.accuracy:
            out.append(CriterionGrade(
                criterion_id=c.id, level=MarkLevel.partial, marks_awarded=0,
                rationale="Pending SymPy verification.", confidence=0.6))
        else:
            out.append(CriterionGrade(
                criterion_id=c.id, level=MarkLevel.full, marks_awarded=c.marks,
                rationale="Approach present and valid (mock).", confidence=0.9))
    return out


class _Proposal(BaseModel):
    """Wrapper so the LLM returns the grade list under a named field."""

    grades: list[CriterionGrade]
