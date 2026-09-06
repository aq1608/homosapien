"""Phase 2: question extraction, whole-paper transcription, not-attempted grading."""
from homosapien.schemas import (
    Criterion,
    CriterionKind,
    MarkScheme,
    Question,
    QuestionType,
    StudentAnswer,
)
from homosapien.tools import extract_questions, grader, ingest


def test_extract_questions_mock_returns_questions():
    qs = extract_questions.extract_from_pdf("ignored/in/mock.pdf")
    assert qs and all(q.id and q.max_marks > 0 for q in qs)
    assert any(q.type is QuestionType.proof for q in qs)  # Q3 is a proof


def test_ingest_paper_one_answer_per_question():
    qs = extract_questions.extract_from_pdf("mock.pdf")
    answers = ingest.ingest_paper("alice", "alice_T1.pdf", qs)
    assert len(answers) == len(qs)
    assert {a.question_id for a in answers} == {q.id for q in qs}
    assert all(a.student_id == "alice" and a.scan_path == "alice_T1.pdf" for a in answers)


def test_not_attempted_is_clean_zero_no_escalation():
    scheme = MarkScheme(
        question_id="Q1", total_marks=2, source="provided", approved=True,
        criteria=[Criterion(id="M1", description="m", marks=2, kind=CriterionKind.method)],
    )
    q = Question(id="Q1", prompt="…", max_marks=2, type=QuestionType.computational)
    blank = StudentAnswer(student_id="s", question_id="Q1", attempted=False)
    g = grader.grade_answer(q, scheme, blank)
    assert g.marks_awarded == 0
    assert not g.escalate                      # blank != illegible
    assert g.error_types == ["not-attempted"]
