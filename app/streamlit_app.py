"""homosapien — educator UI.

Run it:  streamlit run app/streamlit_app.py

Three ways in:
  * Sample cohort      — one click, no files (offline demo).
  * Whole tutorial PDF — upload a tutorial PDF (questions auto-extracted) + one
                         student's handwritten answer PDF. (Phase 2 / real coursework.)
  * Per-question scans — one image/PDF per question, named student__question.ext.

Runs in MOCK with no AWS; set HOMOSAPIEN_LIVE=1 for real Bedrock grading +
handwriting transcription.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

import streamlit as st

from homosapien import config, fixtures
from homosapien.router import detect_workflow
from homosapien.schemas import MarkLevel, Notes, Question, QuestionType
from homosapien.tools import extract_questions, ingest, review
from homosapien.workflows import run_uc1, run_uc2

st.set_page_config(page_title="homosapien — maths grading", page_icon="✍️", layout="wide")

_LEVEL_COLOR = {
    MarkLevel.full: "#2f8f5b",
    MarkLevel.partial: "#b07818",
    MarkLevel.zero: "#c0392b",
}


# --------------------------------------------------------------------------- #
def _session_dir() -> pathlib.Path:
    if "workdir" not in st.session_state:
        st.session_state.workdir = tempfile.mkdtemp(prefix="homosapien_")
    return pathlib.Path(st.session_state.workdir)


def _save(upload) -> str:
    dest = _session_dir() / upload.name
    dest.write_bytes(upload.getbuffer())
    return str(dest)


def _questions_from_rows(rows) -> list[Question]:
    out = []
    for r in rows:
        if not str(r.get("id", "")).strip():
            continue
        out.append(Question(
            id=str(r["id"]).strip(),
            prompt=str(r.get("prompt", "")),
            max_marks=int(r.get("max_marks", 4) or 4),
            type=QuestionType(r.get("type", "computational")),
        ))
    return out


def _rows_from_questions(questions) -> list[dict]:
    return [{"id": q.id, "prompt": q.prompt, "max_marks": q.max_marks, "type": q.type.value}
            for q in questions]


def _questions_editor(default_rows, key) -> list[dict]:
    return st.data_editor(
        default_rows, num_rows="dynamic", use_container_width=True,
        column_config={
            "type": st.column_config.SelectboxColumn(
                "type", options=["computational", "proof"], required=True),
            "max_marks": st.column_config.NumberColumn("max_marks", min_value=1, step=1),
            "prompt": st.column_config.TextColumn("prompt", width="large"),
        },
        key=key,
    )


def _run(questions, notes, answers, mode):
    workflow = detect_workflow(answers)
    if workflow == "UC1":
        reports, insights = [run_uc1(questions, notes, answers)], []
    else:
        reports, insights = run_uc2(questions, notes, answers)
    st.session_state.results = (reports, insights, answers, workflow, mode)


def _render_grade(g, answer, show_image):
    left, right = st.columns([1, 2]) if show_image else (None, st.container())
    if show_image:
        with left:
            if answer and answer.scan_path:
                try:
                    from homosapien.tools import image_prep
                    st.image(image_prep.preview_png(answer.scan_path), use_container_width=True)
                    st.caption(f"legibility {answer.transcription_confidence:.2f}")
                except Exception:
                    st.caption("(scan preview unavailable)")
            else:
                st.caption("No scan (typed answer)")
    with right:
        head = f"**{g.question_id}** — {g.marks_awarded}/{g.max_marks}"
        if g.escalate:
            head += " &nbsp; :orange[⚠ needs review]"
        if not (answer and answer.attempted):
            head += " &nbsp; :gray[· not attempted]"
        st.markdown(head)
        if answer and answer.raw_text:
            st.code(answer.raw_text, language="latex")
            if answer.final_expr:
                st.caption(f"final: `{answer.final_expr}`")
        for cg in g.criteria:
            color = _LEVEL_COLOR.get(cg.level, "#5a6474")
            chk = " `[SymPy]`" if cg.sympy_checked else ""
            st.markdown(
                f"<span style='color:{color}'>●</span> **{cg.criterion_id}** "
                f"<span style='color:{color}'>{cg.level.value}</span> "
                f"{cg.marks_awarded}m{chk} — <span style='color:#5a6474'>{cg.rationale}</span>",
                unsafe_allow_html=True,
            )
        for reason in g.escalation_reasons:
            st.warning(reason, icon="⚠️")


def _render_results():
    reports, insights, answers, workflow, mode = st.session_state.results
    by_key = {(a.student_id, a.question_id): a for a in answers}
    whole_paper = mode == "tutorial"

    st.subheader(f"Review  ·  {workflow}  ·  {len(reports)} student(s)")
    if insights:
        st.info("**Cohort insights**\n\n" + "\n".join(f"- {i.observation}" for i in insights))
    st.download_button(
        "⬇ Download HTML review sheet",
        data=review.build_html(reports, answers),
        file_name="homosapien_review.html", mime="text/html",
    )

    for r in reports:
        needs = sum(1 for g in r.per_question if g.escalate)
        label = f"{r.student_id} — {r.total_awarded}/{r.total_max}" + (
            f"  ⚠ {needs} to review" if needs else "")
        with st.expander(label, expanded=len(reports) == 1):
            st.markdown(r.narrative)
            if whole_paper:  # show the submitted paper once, not per question
                scan = next((a.scan_path for a in answers if a.student_id == r.student_id
                             and a.scan_path), None)
                if scan:
                    try:
                        from homosapien.tools import image_prep
                        with st.expander("📄 Submitted answer PDF", expanded=False):
                            for png in image_prep.to_png_pages(scan):
                                st.image(png, use_container_width=True)
                    except Exception:
                        pass
            for g in r.per_question:
                st.divider()
                _render_grade(g, by_key.get((r.student_id, g.question_id)),
                              show_image=not whole_paper)


# --------------------------------------------------------------------------- #
st.title("✍️ homosapien")
st.caption(f"Grading maths with human judgement · mode: **{config.mode()}**")
st.markdown(
    "Upload a **tutorial** and a student's **handwritten answers** → the agent "
    "grades each step and you **review** it below. New here? Try the sample first."
)
if st.button("▶ Try with sample data (no files needed)"):
    _run(fixtures.QUESTIONS, fixtures.NOTES, fixtures.cohort_answers(), "sample")

with st.sidebar:
    st.header("Input mode")
    input_mode = st.radio(
        "How are you providing answers?",
        ["Whole tutorial PDF", "Per-question scans"],
        captions=[
            "One student's whole handwritten paper + the tutorial PDF",
            "One image/PDF per question (named student__question.ext)",
        ],
    )
    st.divider()
    st.caption(
        "MOCK uses canned model output (SymPy grading is still real). Set "
        "`HOMOSAPIEN_LIVE=1` in `.env` for real Bedrock grading + handwriting "
        "transcription."
    )

# --- Whole tutorial PDF (Phase 2) ------------------------------------------ #
if input_mode == "Whole tutorial PDF":
    st.subheader("1 · Tutorial paper (questions)")
    st.caption("Upload the typed tutorial; the agent extracts the questions. "
               "Marks are **proposed — edit them** in the table before grading.")
    tut = st.file_uploader("Typed tutorial PDF", type=["pdf"], key="tut_pdf")
    if tut and st.button("Extract questions"):
        with st.spinner("Extracting questions…"):
            try:
                qs = extract_questions.extract_from_pdf(_save(tut))
                st.session_state.tut_rows = _rows_from_questions(qs)
                st.success(f"Extracted {len(qs)} question(s) — review & edit marks below.")
            except Exception as exc:
                st.error(f"Extraction failed: {exc}")

    rows = _questions_editor(
        st.session_state.get("tut_rows", _rows_from_questions(fixtures.QUESTIONS)),
        key="tut_editor",
    )

    st.subheader("2 · Lecture notes / formula sheet (context, optional)")
    st.caption("Optional context that helps the agent grade — a formula sheet or slides.")
    note_pdfs = st.file_uploader("Context PDFs", type=["pdf"], accept_multiple_files=True,
                                 key="note_pdfs")

    st.subheader("3 · Student's handwritten answer (one PDF)")
    st.caption("One PDF holding the student's full handwritten submission for this tutorial.")
    student_id = st.text_input("Student id", value="student")
    ans = st.file_uploader("Answer PDF", type=["pdf"], key="ans_pdf")

    if st.button("▶ Grade tutorial", type="primary"):
        questions = _questions_from_rows(rows)
        if not questions:
            st.error("No questions — extract or add at least one.")
        elif not ans:
            st.error("Upload the student's answer PDF.")
        else:
            try:
                with st.spinner("Transcribing and grading…"):
                    notes = (extract_questions.notes_from_pdfs([_save(n) for n in note_pdfs])
                             if note_pdfs else Notes(text=""))
                    answers = ingest.ingest_paper(student_id, _save(ans), questions)
                    _run(questions, notes, answers, "tutorial")
            except Exception as exc:
                st.error(f"Grading failed: {exc}")

# --- Per-question scans (Phase 1) ------------------------------------------ #
elif input_mode == "Per-question scans":
    st.subheader("1 · Questions & lecture notes")
    st.caption("Edit the questions and **marks** (proposed, editable); paste your notes.")
    rows = _questions_editor(_rows_from_questions(fixtures.QUESTIONS), key="pq_editor")
    notes_text = st.text_area("Lecture notes", value=fixtures.NOTES.text, height=100)

    st.subheader("2 · Upload scans")
    st.caption("Name files `student__question.ext` (e.g. `alice__Q1.pdf`).")
    uploads = st.file_uploader("Scans (PNG / JPG / PDF)", type=["png", "jpg", "jpeg", "pdf"],
                               accept_multiple_files=True, key="pq_uploads")
    if uploads:
        questions = _questions_from_rows(rows)
        default_q = questions[0].id if questions else "Q1"
        mapping_rows = []
        for f in uploads:
            stem = pathlib.Path(f.name).stem
            sid, qid = (stem.split("__", 1) if "__" in stem
                        else (stem.split("_", 1) if "_" in stem else (stem, default_q)))
            mapping_rows.append({"file": f.name, "student_id": sid, "question_id": qid})
        mapping = st.data_editor(mapping_rows, use_container_width=True, key="map_editor")
        if st.button("▶ Grade scans", type="primary"):
            try:
                with st.spinner("Transcribing and grading…"):
                    by_name = {f.name: f for f in uploads}
                    answers = [ingest.ingest_answer(m["student_id"], m["question_id"],
                                                    _save(by_name[m["file"]])) for m in mapping]
                    _run(questions, Notes(text=notes_text), answers, "scans")
            except Exception as exc:
                st.error(f"Grading failed: {exc}")

# --------------------------------------------------------------------------- #
st.divider()
if "results" in st.session_state:
    _render_results()
else:
    st.info("Pick an input mode on the left (or load the sample cohort) to see graded reports.")
