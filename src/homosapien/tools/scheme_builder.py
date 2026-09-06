"""Produce an approved, per-criterion mark scheme for a question.

Two entry points (you asked for both):
  * an educator-provided scheme is parsed into structured criteria;
  * otherwise a scheme is *drafted* from the question + notes.

Either way the result must be approved (human-in-the-loop) before grading. In
MOCK mode a representative scheme is returned; ``approve()`` flips the gate.
"""
from __future__ import annotations

from ..llm import run_structured
from ..schemas import (
    Criterion,
    CriterionKind,
    MarkScheme,
    Notes,
    Question,
    QuestionType,
)

_SYSTEM_PROMPT = """You are a university mathematics examiner. Given a question
and the lecture notes, draft a mark scheme as a list of criteria. Split marks
into method (M) and accuracy (A) marks for computational questions, or logical
milestones for proofs. State acceptable alternative methods. For accuracy
criteria include the expected final expression, written so a computer-algebra
system can parse it (use * for multiplication, e.g. 'x*exp(x) - exp(x) + C').
Use UNIQUE, sequential criterion ids: method marks M1, M2, ...; accuracy marks
A1, A2, ...; proof milestones L1, L2, .... Never reuse an id. Be strict about the
total."""


def build_or_load(
    question: Question,
    notes: Notes,
    provided: MarkScheme | None = None,
) -> MarkScheme:
    """Return a mark scheme, from a provided one or freshly drafted."""
    if provided is not None:
        provided.source = "provided"
        return _finalize(provided, question)

    def _mock() -> MarkScheme:
        return _mock_scheme(question)

    user = f"QUESTION ({question.type.value}, {question.max_marks} marks):\n" \
           f"{question.prompt}\n\nLECTURE NOTES:\n{notes.text[:4000]}"
    scheme = run_structured(_SYSTEM_PROMPT, user, MarkScheme, _mock)
    scheme.source = "drafted"
    return _finalize(scheme, question)


def _finalize(scheme: MarkScheme, question: Question) -> MarkScheme:
    """Guarantee unique criterion ids and a consistent total before grading."""
    ids = [c.id for c in scheme.criteria]
    if len(ids) != len(set(ids)):
        _renumber_ids(scheme)
    scheme.total_marks = sum(c.marks for c in scheme.criteria)
    scheme.question_id = question.id
    return scheme


def _renumber_ids(scheme: MarkScheme) -> None:
    """Assign sequential, kind-prefixed ids (M1, A1, L1, ...) in place."""
    prefix = {
        CriterionKind.method: "M",
        CriterionKind.accuracy: "A",
        CriterionKind.logic: "L",
    }
    counters: dict[str, int] = {}
    for c in scheme.criteria:
        p = prefix.get(c.kind, "C")
        counters[p] = counters.get(p, 0) + 1
        c.id = f"{p}{counters[p]}"


def approve(scheme: MarkScheme) -> MarkScheme:
    """Educator sign-off. Grading refuses to run on an unapproved scheme."""
    scheme.approved = True
    return scheme


def _mock_scheme(question: Question) -> MarkScheme:
    if question.type is QuestionType.proof:
        criteria = [
            Criterion(id="L1", description="States assumption / sets up contradiction",
                      marks=1, kind=CriterionKind.logic),
            Criterion(id="L2", description="Each inference valid, no gaps",
                      marks=2, kind=CriterionKind.logic),
            Criterion(id="L3", description="Reaches the required conclusion (QED)",
                      marks=1, kind=CriterionKind.logic),
        ]
    else:
        criteria = [
            Criterion(id="M1", description="Selects a correct method",
                      marks=1, kind=CriterionKind.method, accepts_alternatives=True),
            Criterion(id="A1", description="Correct intermediate expression",
                      marks=1, kind=CriterionKind.accuracy,
                      expected_expr="x*exp(x) - exp(x)"),
            Criterion(id="A2", description="Correct final answer",
                      marks=2, kind=CriterionKind.accuracy,
                      expected_expr="exp(x)*(x - 1)"),
        ]
    return MarkScheme(
        question_id=question.id,
        total_marks=sum(c.marks for c in criteria),
        criteria=criteria,
        source="drafted",
    )
