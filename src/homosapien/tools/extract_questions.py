"""Turn a typed tutorial PDF into gradable Question objects, and PDFs into Notes.

Tutorial papers are digital (PyMuPDF extracts their text cleanly). An LLM
structuring pass turns that text into per-question objects with a *proposed*
mark allocation the educator then edits in the UI. Graded questions only —
[OPTIONAL]/practice items and general instructions are dropped.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from .. import config
from ..llm import run_structured
from ..schemas import Notes, Question, QuestionType
from . import image_prep

_SYSTEM_PROMPT = """You are a university mathematics examiner. From the raw text
of a tutorial paper, extract the questions that are graded for submission. For
each, return: id (Q1, Q2, ...), prompt (the full question including its sub-parts),
a PROPOSED max_marks (a sensible integer the educator can adjust), and type
(computational for calculate/evaluate/solve, proof for prove/show/derive).
Ignore general instructions and any question marked [OPTIONAL] or 'practice'."""


class _Questions(BaseModel):
    questions: list[Question]


def _pdf_text(path: str | Path) -> str:
    pymupdf = image_prep._require("pymupdf")
    with pymupdf.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


def extract_from_pdf(pdf: str | Path) -> list[Question]:
    """Extract graded questions from a typed tutorial PDF (proposed marks)."""
    if not config.LIVE:  # offline: don't require the file to exist
        return [q.model_copy() for q in _MOCK_TOPIC1]

    text = _pdf_text(pdf)

    def _mock() -> _Questions:
        return _Questions(questions=[q.model_copy() for q in _MOCK_TOPIC1])

    user = f"TUTORIAL PAPER TEXT:\n{text[:8000]}"
    return run_structured(_SYSTEM_PROMPT, user, _Questions, _mock).questions


def notes_from_pdfs(paths: list[str | Path], *, cap: int = 6000) -> Notes:
    """Concatenate typed text from context PDFs (formula sheet, slides) as notes."""
    chunks = []
    for p in paths:
        try:
            chunks.append(_pdf_text(p))
        except Exception as exc:  # pragma: no cover - defensive
            chunks.append(f"[could not read {Path(p).name}: {exc}]")
    return Notes(text="\n\n".join(chunks)[:cap])


# Offline stand-in so the UI works without Bedrock.
_MOCK_TOPIC1 = [
    Question(id="Q1", type=QuestionType.computational, max_marks=4,
             prompt="Find the sum of the first n terms of the arithmetic series 3, 7, 11, ..."),
    Question(id="Q2", type=QuestionType.computational, max_marks=4,
             prompt="Evaluate the geometric series sum_{k=0}^{n-1} a r^k and state when it converges."),
    Question(id="Q3", type=QuestionType.proof, max_marks=5,
             prompt="Prove by induction that sum_{i=1}^{n} i = n(n+1)/2 for all n >= 1."),
]
