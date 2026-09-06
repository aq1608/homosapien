"""Self-contained HTML review sheet: the educator's QA of the machine's grade.

For each student, each question shows the original scan (embedded) beside the
transcript and the per-criterion marks, with escalations and low-confidence
regions surfaced up top. Images are embedded as base64 so the file is portable
(email it, open offline). This complements — it does not replace — the
student-facing narrative report.
"""
from __future__ import annotations

import base64
import html

from ..schemas import AnswerGrade, MarkLevel, StudentAnswer, StudentReport

_LEVEL_COLOR = {
    MarkLevel.full: "#2f8f5b",
    MarkLevel.partial: "#b07818",
    MarkLevel.zero: "#c0392b",
}


def build_html(
    reports: list[StudentReport],
    answers: list[StudentAnswer],
    *,
    title: str = "homosapien — grading review",
) -> str:
    """Render all students into one self-contained HTML review document."""
    by_key = {(a.student_id, a.question_id): a for a in answers}
    total_escalations = sum(
        1 for r in reports for g in r.per_question if g.escalate
    )

    parts = [_HEAD.format(title=html.escape(title))]
    parts.append(f'<h1>{html.escape(title)}</h1>')
    parts.append(
        f'<p class="meta">{len(reports)} student(s) · '
        f'<span class="flag">{total_escalations} question(s) need review</span></p>'
    )

    # Cohort index
    parts.append('<div class="index"><h2>Students</h2><ul>')
    for r in reports:
        needs = sum(1 for g in r.per_question if g.escalate)
        badge = f' <span class="flag">({needs} to review)</span>' if needs else ""
        parts.append(
            f'<li><a href="#{html.escape(r.student_id)}">'
            f'{html.escape(r.student_id)}</a> — {r.total_awarded}/{r.total_max}{badge}</li>'
        )
    parts.append("</ul></div>")

    for r in reports:
        parts.append(_render_student(r, by_key))

    parts.append("</body></html>")
    return "".join(parts)


def _render_student(r: StudentReport, by_key: dict) -> str:
    out = [f'<section class="student" id="{html.escape(r.student_id)}">']
    out.append(
        f'<h2>{html.escape(r.student_id)} '
        f'<span class="score">{r.total_awarded}/{r.total_max}</span></h2>'
    )
    out.append(f'<p class="narrative">{html.escape(r.narrative)}</p>')

    for g in r.per_question:
        answer = by_key.get((r.student_id, g.question_id))
        out.append(_render_question(g, answer))
    out.append("</section>")
    return "".join(out)


def _render_question(g: AnswerGrade, answer: StudentAnswer | None) -> str:
    flag = ' <span class="flag">⚠ needs review</span>' if g.escalate else ""
    out = [f'<div class="q"><h3>{html.escape(g.question_id)} '
           f'<span class="score">{g.marks_awarded}/{g.max_marks}</span>{flag}</h3>']

    out.append('<div class="cols">')

    # Left: the original scan (if any)
    out.append('<div class="scan">')
    img = _embed_image(answer)
    if img:
        conf = answer.transcription_confidence if answer else 1.0
        out.append(f'<img src="{img}" alt="scan"/>')
        out.append(f'<p class="conf">legibility {conf:.2f}</p>')
    else:
        out.append('<p class="noimg">No scan (typed answer)</p>')
    out.append("</div>")

    # Right: transcript + grades
    out.append('<div class="detail">')
    if answer and answer.raw_text:
        out.append('<p class="lbl">Transcript</p>')
        out.append(f'<pre class="latex">{html.escape(answer.raw_text)}</pre>')
        if answer.final_expr:
            out.append(f'<p class="final">final: <code>{html.escape(answer.final_expr)}</code></p>')

    out.append('<p class="lbl">Marks</p>')
    for cg in g.criteria:
        color = _LEVEL_COLOR.get(cg.level, "#5a6474")
        chk = ' <span class="sympy">[SymPy]</span>' if cg.sympy_checked else ""
        out.append(
            f'<div class="crit"><span class="dot" style="background:{color}"></span>'
            f'<b>{html.escape(cg.criterion_id)}</b> '
            f'<span style="color:{color}">{cg.level.value}</span> '
            f'{cg.marks_awarded}m{chk}<br><span class="why">{html.escape(cg.rationale)}</span></div>'
        )
    for reason in g.escalation_reasons:
        out.append(f'<div class="esc">↳ {html.escape(reason)}</div>')
    out.append("</div>")

    out.append("</div></div>")
    return "".join(out)


def _embed_image(answer: StudentAnswer | None) -> str | None:
    if not answer or not answer.scan_path:
        return None
    try:
        from . import image_prep

        png = image_prep.preview_png(answer.scan_path)
        b64 = base64.b64encode(png).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return None  # never let a preview failure break the review sheet


_HEAD = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>
body{{font-family:system-ui,sans-serif;max-width:1000px;margin:0 auto;padding:24px;color:#1b2230;background:#f4f6f9}}
h1{{margin:0 0 4px}} .meta{{color:#5a6474;margin-top:0}}
.flag{{color:#b07818;font-weight:600}}
.index{{background:#fff;border:1px solid #d8dde5;border-radius:12px;padding:12px 20px;margin:16px 0}}
.index ul{{margin:6px 0;padding-left:18px}} .index a{{color:#2c3a80}}
.student{{background:#fff;border:1px solid #d8dde5;border-radius:14px;padding:20px;margin:18px 0}}
.score{{font-family:ui-monospace,monospace;color:#2c3a80;font-weight:600}}
.narrative{{white-space:pre-wrap;color:#31404f}}
.q{{border-top:1px solid #e6eaf1;padding-top:14px;margin-top:14px}}
.cols{{display:flex;gap:18px;flex-wrap:wrap}}
.scan{{flex:1;min-width:220px}} .scan img{{max-width:100%;border:1px solid #d8dde5;border-radius:8px}}
.conf{{font-size:.8rem;color:#5a6474}} .noimg{{color:#8892a2;font-style:italic}}
.detail{{flex:2;min-width:280px}}
.lbl{{font-family:ui-monospace,monospace;font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;color:#5a6474;margin:10px 0 4px}}
.latex{{background:#f1f3f7;border:1px solid #e6eaf1;border-radius:8px;padding:10px;white-space:pre-wrap;font-size:.9rem}}
.final code{{background:#e6e9f6;padding:2px 6px;border-radius:5px}}
.crit{{padding:6px 0;border-bottom:1px dashed #e6eaf1}}
.crit .dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}}
.why{{color:#5a6474;font-size:.88rem}} .sympy{{font-family:ui-monospace,monospace;font-size:.75rem;color:#2c3a80}}
.esc{{background:#f6ecd6;border-radius:6px;padding:6px 10px;margin-top:6px;font-size:.85rem;color:#8a5a12}}
</style></head><body>"""
