"""Turn a scanned handwritten script into structured, ordered LaTeX steps.

Highest-risk component in the whole system. It is governed by one rule (see
``FAIRNESS_RULE``): a student is never marked down for the OCR's mistake — when
legibility is low the *page* is escalated, never converted into a lost mark.

LIVE: a direct Amazon Bedrock Converse call with an image block (Claude Sonnet
4.5 is vision-capable), returning structured JSON. MOCK: a deterministic,
varied transcription so the whole UI/pipeline runs offline.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from .. import config
from ..llm import _extract_json
from ..schemas import TranscriptionRegion
from . import image_prep

FAIRNESS_RULE = (
    "Never penalise a student for transcription uncertainty. If a region is not "
    "legible enough to grade fairly, escalate the page instead of guessing."
)


@dataclass
class Transcription:
    latex: str
    confidence: float
    final_expr: str | None = None
    regions: list[TranscriptionRegion] = field(default_factory=list)
    notes: str = ""
    attempted: bool = True


_SYSTEM_PROMPT = f"""You transcribe scanned handwritten university mathematics.
Copy what is written faithfully in LaTeX — do NOT correct the student's maths.
Read steps top-to-bottom, in order. Segment the work into regions and give each
a legibility confidence in [0,1]. Also extract the student's FINAL expression in
a form a computer-algebra system can parse (use * for multiplication, ^ or ** for
powers, exp() for e^x); use null if there is no single final expression (e.g. a
proof). {FAIRNESS_RULE}

Respond with ONLY JSON:
{{"steps_latex": "...", "final_expr": "... or null",
  "regions": [{{"text": "...", "confidence": 0.0, "kind": "working|final|header"}}],
  "overall_confidence": 0.0}}"""


def transcribe(scan_path: str) -> Transcription:
    """Read a scan into LaTeX + a legibility confidence in [0, 1]."""
    if not config.LIVE:
        return _mock(scan_path)

    import boto3

    pages = image_prep.to_png_pages(scan_path)
    content: list[dict] = [{"text": "Transcribe this student's answer."}]
    for png in pages:
        content.append({"image": {"format": "png", "source": {"bytes": png}}})

    client = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)
    resp = client.converse(
        modelId=config.MODEL_ID,
        system=[{"text": _SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": content}],
        inferenceConfig={"maxTokens": 2000, "temperature": 0.0},
    )
    text = resp["output"]["message"]["content"][0]["text"]
    data = _extract_json(text)

    regions = [
        TranscriptionRegion(
            text=r.get("text", ""),
            confidence=float(r.get("confidence", 1.0)),
            kind=r.get("kind", "working"),
        )
        for r in data.get("regions", [])
    ]
    # Fairness: the page is only as trustworthy as its weakest region.
    region_min = min((r.confidence for r in regions), default=None)
    overall = float(data.get("overall_confidence", region_min or 1.0))
    confidence = min(overall, region_min) if region_min is not None else overall

    final = data.get("final_expr")
    if isinstance(final, str) and final.strip().lower() in {"null", "none", ""}:
        final = None

    return Transcription(
        latex=data.get("steps_latex", ""),
        confidence=confidence,
        final_expr=final,
        regions=regions,
        notes=f"Transcribed {len(pages)} page(s) from {Path(scan_path).name}",
    )


_PAPER_SYSTEM_PROMPT = f"""You transcribe a scanned handwritten mathematics
tutorial. The student is answering a known list of questions. Read every page,
transcribe faithfully in LaTeX (do NOT correct the maths), and GROUP the work by
question id. For each question the student attempted, give the steps and the
final expression (CAS-parseable, use * for multiplication, exp() for e^x; null if
none/proof). Mark a question attempted=false if the student left it blank. Give a
per-question legibility confidence in [0,1]. {FAIRNESS_RULE}

Respond with ONLY JSON:
{{"answers": [{{"question_id": "Q1", "attempted": true, "steps_latex": "...",
  "final_expr": "... or null", "confidence": 0.0,
  "regions": [{{"text": "...", "confidence": 0.0, "kind": "working|final"}}]}}]}}"""


def transcribe_paper(scan_path: str, questions) -> dict[str, Transcription]:
    """Transcribe one multi-page handwritten paper, grouped by question id.

    ``questions`` is a list of objects with ``.id`` and ``.prompt``. Returns a
    mapping question_id -> Transcription for every question the student attempted.
    """
    if not config.LIVE:
        return _mock_paper(scan_path, questions)

    import boto3

    pages = image_prep.to_png_pages(scan_path)
    qlist = "\n".join(f"{q.id}: {q.prompt[:200]}" for q in questions)
    content: list[dict] = [
        {"text": f"The student is answering these questions:\n{qlist}\n\n"
                 "Transcribe their handwriting and group the work by question id."}
    ]
    for png in pages:
        content.append({"image": {"format": "png", "source": {"bytes": png}}})

    client = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)
    resp = client.converse(
        modelId=config.MODEL_ID,
        system=[{"text": _PAPER_SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": content}],
        inferenceConfig={"maxTokens": 4000, "temperature": 0.0},
    )
    data = _extract_json(resp["output"]["message"]["content"][0]["text"])

    out: dict[str, Transcription] = {}
    for a in data.get("answers", []):
        qid = a.get("question_id")
        if not qid:
            continue
        regions = [
            TranscriptionRegion(text=r.get("text", ""),
                                confidence=float(r.get("confidence", 1.0)),
                                kind=r.get("kind", "working"))
            for r in a.get("regions", [])
        ]
        final = a.get("final_expr")
        if isinstance(final, str) and final.strip().lower() in {"null", "none", ""}:
            final = None
        out[qid] = Transcription(
            latex=a.get("steps_latex", ""),
            confidence=float(a.get("confidence", 1.0)),
            final_expr=final,
            regions=regions,
            attempted=bool(a.get("attempted", True)),
            notes=f"From {Path(scan_path).name} ({len(pages)} pages)",
        )
    return out


# --------------------------------------------------------------------------- #
# Deterministic mock: varies by file so an offline cohort looks realistic.
_MOCK_VARIANTS = [
    dict(latex=r"u=x,\ dv=e^{x}dx;\ = x e^{x} - \int e^{x}dx = e^{x}(x-1)",
         final_expr="exp(x)*(x-1)", confidence=0.94, note="clean"),
    dict(latex=r"by parts; = x e^{x} + e^{x}  (sign slip)",
         final_expr="x*exp(x)+exp(x)", confidence=0.9, note="sign slip"),
    dict(latex=r"= x e^{x} - e^{x} + C  (edge of legibility)",
         final_expr="exp(x)*(x-1)", confidence=0.58, note="smudged — low legibility"),
]


def _mock(scan_path: str) -> Transcription:
    idx = int(hashlib.md5(str(scan_path).encode()).hexdigest(), 16) % len(_MOCK_VARIANTS)
    v = _MOCK_VARIANTS[idx]
    return Transcription(
        latex=v["latex"],
        confidence=v["confidence"],
        final_expr=v["final_expr"],
        regions=[
            TranscriptionRegion(text=v["latex"], confidence=v["confidence"], kind="working"),
            TranscriptionRegion(text=v["final_expr"], confidence=v["confidence"], kind="final"),
        ],
        notes=f"MOCK ({v['note']}) for {Path(scan_path).name}",
    )


def _mock_paper(scan_path: str, questions) -> dict[str, Transcription]:
    """Offline whole-paper transcription: varied, deterministic per question."""
    out: dict[str, Transcription] = {}
    for q in questions:
        h = int(hashlib.md5(f"{scan_path}:{q.id}".encode()).hexdigest(), 16) % 4
        is_proof = getattr(getattr(q, "type", None), "value", "") == "proof"
        if h == 3:  # left blank
            out[q.id] = Transcription(latex="", confidence=1.0, attempted=False,
                                      notes=f"{q.id}: not attempted (mock)")
            continue
        conf = 0.58 if h == 2 else 0.9
        final = None if is_proof else ["n*(n+1)/2", "n**2", "(1-r**n)/(1-r)"][h % 3]
        latex = f"handwritten working for {q.id}" + (" (edge of legibility)" if h == 2 else "")
        out[q.id] = Transcription(
            latex=latex, confidence=conf, final_expr=final, attempted=True,
            regions=[TranscriptionRegion(text=latex, confidence=conf, kind="working")],
            notes=f"MOCK paper for {q.id}",
        )
    return out
