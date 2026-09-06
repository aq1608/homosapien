"""Typed data model shared across the whole pipeline.

The flow of objects is:

    Question + Notes  --scheme_builder-->  MarkScheme (criteria)
    StudentAnswer     --grader---------->  AnswerGrade (per-criterion)
    AnswerGrade[]     --report_writer--->  StudentReport
    AnswerGrade[]     --cohort_insights->  CohortInsight[]
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    computational = "computational"  # has a checkable answer -> SymPy path
    proof = "proof"                  # logical-validity path


class MarkLevel(str, Enum):
    full = "full"
    partial = "partial"
    zero = "zero"


class CriterionKind(str, Enum):
    method = "method"      # M-mark: the right approach
    accuracy = "accuracy"  # A-mark: the right result (SymPy-gated)
    logic = "logic"        # a proof milestone


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
class Notes(BaseModel):
    """Lecture notes used as grading context."""

    text: str


class Question(BaseModel):
    id: str
    prompt: str
    max_marks: int
    type: QuestionType = QuestionType.computational


class Criterion(BaseModel):
    """One rubric line, e.g. M1 / A1."""

    id: str
    description: str
    marks: int
    kind: CriterionKind = CriterionKind.method
    accepts_alternatives: bool = False
    # For computational accuracy criteria: the expected expression, checked with
    # SymPy against the student's final expression.
    expected_expr: str | None = None


class MarkScheme(BaseModel):
    question_id: str
    total_marks: int
    criteria: list[Criterion]
    source: str = "drafted"   # "drafted" (agent) | "provided" (educator)
    approved: bool = False    # human-in-the-loop gate before grading


class TranscriptionRegion(BaseModel):
    """One transcribed region of a scan, with its legibility confidence."""

    text: str
    confidence: float = 1.0
    kind: str = "working"  # working | final | header


class StudentAnswer(BaseModel):
    student_id: str
    question_id: str
    # Typed or transcribed working (LaTeX-ish). Populated by vision_transcribe
    # for scanned scripts.
    raw_text: str | None = None
    # Extracted final expression, if any — the thing SymPy verifies.
    final_expr: str | None = None
    scan_path: str | None = None
    transcription_confidence: float = 1.0
    # Per-region reads from the scan (for highlighting weak spots in review).
    regions: list[TranscriptionRegion] = Field(default_factory=list)
    transcription_notes: str | None = None
    # False when the student left this question blank (a legitimate zero, not an
    # escalation). Set by whole-paper transcription.
    attempted: bool = True


# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #
class CriterionGrade(BaseModel):
    criterion_id: str
    level: MarkLevel
    marks_awarded: int
    rationale: str
    sympy_checked: bool = False
    confidence: float = 1.0


class AnswerGrade(BaseModel):
    student_id: str
    question_id: str
    criteria: list[CriterionGrade]
    marks_awarded: int
    max_marks: int
    error_types: list[str] = Field(default_factory=list)
    escalate: bool = False
    escalation_reasons: list[str] = Field(default_factory=list)


class StudentReport(BaseModel):
    student_id: str
    total_awarded: int
    total_max: int
    per_question: list[AnswerGrade]
    narrative: str
    strengths: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class CohortInsight(BaseModel):
    question_id: str
    observation: str
    affected_students: list[str] = Field(default_factory=list)
