"""The SymPy gate + fairness rules in the grader (runs in MOCK mode; SymPy real)."""
from homosapien.schemas import (
    Criterion,
    CriterionKind,
    MarkLevel,
    MarkScheme,
    Question,
    QuestionType,
    StudentAnswer,
)
from homosapien.tools import grader


def _computational_scheme(expected: str) -> MarkScheme:
    return MarkScheme(
        question_id="Q1",
        total_marks=2,
        source="provided",
        approved=True,
        criteria=[
            Criterion(id="M1", description="method", marks=1, kind=CriterionKind.method),
            Criterion(id="A1", description="final answer", marks=1,
                      kind=CriterionKind.accuracy, expected_expr=expected),
        ],
    )


_Q = Question(id="Q1", prompt="Evaluate ∫ x e^x dx.", max_marks=2,
              type=QuestionType.computational)


def _grade(expected, final_expr):
    scheme = _computational_scheme(expected)
    answer = StudentAnswer(student_id="S1", question_id="Q1", final_expr=final_expr)
    return grader.grade_answer(_Q, scheme, answer)


def _a1(grade):
    return next(cg for cg in grade.criteria if cg.criterion_id == "A1")


def test_correct_answer_awarded_via_sympy():
    grade = _grade("x*exp(x) - exp(x)", "exp(x)*(x-1)")
    a1 = _a1(grade)
    assert a1.level is MarkLevel.full and a1.sympy_checked


def test_missing_plus_c_awards_and_escalates_not_zero():
    # The exact LIVE-bug case: correct answer, scheme expected "+ C".
    grade = _grade("x e^x - e^x + C", "exp(x)*(x-1)")
    a1 = _a1(grade)
    assert a1.level is MarkLevel.full          # not zeroed
    assert grade.escalate                        # +C policy handed to the human
    assert any("+C" in r or "constant" in r for r in grade.escalation_reasons)


def test_wrong_answer_is_zeroed():
    grade = _grade("x*exp(x) - exp(x)", "x*exp(x) + exp(x)")
    a1 = _a1(grade)
    assert a1.level is MarkLevel.zero and a1.sympy_checked


def test_unparseable_expected_escalates_and_does_not_penalise():
    # If SymPy can't parse, that's OUR uncertainty — escalate, never force zero.
    grade = _grade("x +", "exp(x)*(x-1)")
    a1 = _a1(grade)
    assert not a1.sympy_checked                  # gate could not verify
    assert a1.level is not MarkLevel.zero         # not force-zeroed by the gate
    assert grade.escalate
