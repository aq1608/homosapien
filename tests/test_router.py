import pytest

from homosapien.router import detect_workflow, dispatch_grader
from homosapien.schemas import Question, QuestionType, StudentAnswer


def _ans(student):
    return StudentAnswer(student_id=student, question_id="Q1")


def test_detect_uc1():
    assert detect_workflow([_ans("S1"), _ans("S1")]) == "UC1"


def test_detect_uc2():
    assert detect_workflow([_ans("S1"), _ans("S2")]) == "UC2"


def test_detect_requires_answers():
    with pytest.raises(ValueError):
        detect_workflow([])


def test_dispatch():
    comp = Question(id="Q1", prompt="", max_marks=4, type=QuestionType.computational)
    proof = Question(id="Q2", prompt="", max_marks=4, type=QuestionType.proof)
    assert dispatch_grader(comp) == "computational"
    assert dispatch_grader(proof) == "proof"
