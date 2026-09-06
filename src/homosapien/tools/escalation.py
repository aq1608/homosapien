"""The escalation contract: what the agent hands back to the educator.

The whole point of the theme — run the busywork unattended, interrupt only for a
real decision. This module decides, deterministically, when a grade should not
be applied automatically.
"""
from __future__ import annotations

from .. import config
from ..schemas import CriterionGrade, CriterionKind, MarkLevel, StudentAnswer


def evaluate(
    criteria: list[CriterionGrade],
    answer: StudentAnswer,
    *,
    threshold: float | None = None,
) -> tuple[bool, list[str]]:
    """Return ``(should_escalate, reasons)`` for a graded answer."""
    thr = config.CONFIDENCE_THRESHOLD if threshold is None else threshold
    reasons: list[str] = []

    if answer.transcription_confidence < thr:
        reasons.append(
            f"scan legibility {answer.transcription_confidence:.2f} < {thr:.2f} "
            "— reading the working may be unreliable"
        )

    for cg in criteria:
        if cg.confidence < thr:
            reasons.append(
                f"{cg.criterion_id}: grade confidence {cg.confidence:.2f} < {thr:.2f}"
            )
        # A partial accuracy mark that was NOT settled by SymPy is a judgement
        # call, not a fact — hand it back.
        if (
            cg.level is MarkLevel.partial
            and not cg.sympy_checked
            and _is_accuracy(cg)
        ):
            reasons.append(
                f"{cg.criterion_id}: partial accuracy mark not verified by SymPy"
            )

    return (bool(reasons), reasons)


def _is_accuracy(cg: CriterionGrade) -> bool:
    # Convention: accuracy criterion ids start with "A".
    return cg.criterion_id.upper().startswith("A")
