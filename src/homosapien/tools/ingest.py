"""Turn scanned scripts into StudentAnswer objects the workflows can grade.

Directory convention:  scans/<student_id>/<question_id>.<ext>
e.g.  scans/alice/Q1.pdf,  scans/alice/Q2.jpg,  scans/bob/Q1.png

Each file is transcribed (see vision_transcribe) and mapped to a StudentAnswer,
carrying the scan path + transcription confidence so the escalation contract and
the review surface can use them.
"""
from __future__ import annotations

from pathlib import Path

from ..schemas import StudentAnswer
from . import vision_transcribe

_SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".tif", ".tiff", ".bmp"}


def ingest_answer(student_id: str, question_id: str, path: str) -> StudentAnswer:
    """Transcribe one scan into a StudentAnswer."""
    t = vision_transcribe.transcribe(path)
    return StudentAnswer(
        student_id=student_id,
        question_id=question_id,
        raw_text=t.latex,
        final_expr=t.final_expr,
        scan_path=str(path),
        transcription_confidence=t.confidence,
        regions=t.regions,
        transcription_notes=t.notes,
    )


def ingest_paper(student_id: str, path: str, questions) -> list[StudentAnswer]:
    """One multi-page handwritten PDF -> one StudentAnswer per question.

    Uses whole-paper transcription guided by the known questions, so a single
    tutorial submission is segmented into per-question answers. Questions the
    student left blank come back as ``attempted=False`` (a legitimate zero).
    """
    trans = vision_transcribe.transcribe_paper(path, questions)
    answers: list[StudentAnswer] = []
    for q in questions:
        t = trans.get(q.id)
        if t is None or not t.attempted:
            answers.append(StudentAnswer(
                student_id=student_id, question_id=q.id, scan_path=str(path),
                attempted=False, transcription_confidence=1.0,
                transcription_notes=(t.notes if t else "not found in scan"),
            ))
        else:
            answers.append(StudentAnswer(
                student_id=student_id, question_id=q.id,
                raw_text=t.latex, final_expr=t.final_expr, scan_path=str(path),
                transcription_confidence=t.confidence, regions=t.regions,
                attempted=True, transcription_notes=t.notes,
            ))
    return answers


def ingest_dir(root: str) -> list[StudentAnswer]:
    """Ingest every scan under ``root`` following the directory convention."""
    root_path = Path(root)
    if not root_path.is_dir():
        raise NotADirectoryError(f"Scans directory not found: {root}")

    answers: list[StudentAnswer] = []
    for student_dir in sorted(p for p in root_path.iterdir() if p.is_dir()):
        for scan in sorted(student_dir.iterdir()):
            if scan.suffix.lower() not in _SUPPORTED:
                continue
            answers.append(
                ingest_answer(student_dir.name, scan.stem, str(scan))
            )
    if not answers:
        raise ValueError(
            f"No scans found under {root}. Expected scans/<student>/<question>.<ext>."
        )
    return answers
