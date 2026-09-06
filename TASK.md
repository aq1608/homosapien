# TASK — Handwriting ingestion + educator review

**Status:** proposed plan, awaiting your go-ahead. Nothing here is built yet.
**Scope:** four deliverables — (1) LIVE `vision_transcribe`, (2) `ingest.py`,
(3) an educator **review surface** that shows the original scan next to the
transcript and the marks, so a human can verify the machine's read and grade,
and (4) a **Streamlit web UI** where the educator uploads files and reviews the
reports interactively.

**UI choice:** Streamlit — fastest educator-facing app that plugs straight into
the pipeline, with native file upload + image display, run locally with Bedrock
creds. The self-contained HTML from `review.py` remains a shareable/downloadable
export. (A claude.ai Artifact can't run the pipeline or call Bedrock, so it can't
be the interactive app.)

Everything is **additive and behind the `LIVE` flag**. MOCK stays the default,
and the typed-input path (`StudentAnswer.raw_text` / `final_expr`) keeps working,
so a flaky scan can never break the grading demo.

---

## Decisions / assumptions (tell me to change any of these)

1. **Vision model:** Claude Sonnet 4.5 on Bedrock (AWS-native, on-theme). Called
   via a **direct `bedrock-runtime` Converse** with an image block — simpler and
   more controllable than routing an image through a Strands agent loop.
   *Fallback if math accuracy disappoints:* a dedicated math-OCR API (e.g.
   MathPix) — external/paid, kept in the back pocket, not built now.
2. **One scan = one question** for v1. Auto-detecting question boundaries from a
   whole-paper scan is deferred (listed in Out of scope).
3. **Input layout convention:** `scans/<student_id>/<question_id>.<ext>`
   (`.png`, `.jpg`, `.pdf`). A multi-page PDF is rasterized and stitched.
   Optional `manifest.json` override supported later if you want explicit mapping.
4. **Review surface = a self-contained HTML "review sheet"** per student, plus a
   cohort index. The scan image is embedded as a base64 data URI so the file is
   portable (email it, open offline). This is for the **educator to QA** — it is
   distinct from the student-facing narrative report.
5. **Fairness rule is enforced here:** page confidence = the *minimum* region
   confidence; below threshold → the page is escalated (flagged, not graded); an
   ambiguous symbol is read in the student's favour or escalated. Never a lost
   mark for OCR uncertainty.

---

## New / changed files

| File | Change |
|---|---|
| `src/homosapien/tools/vision_transcribe.py` | Implement the LIVE path (currently raises `NotImplementedError`). |
| `src/homosapien/tools/image_prep.py` | **New.** Load images; rasterize PDFs (PyMuPDF); resize/compress to Bedrock limits. |
| `src/homosapien/tools/ingest.py` | **New.** `scans → list[StudentAnswer]` (single + batch, directory convention). |
| `src/homosapien/tools/review.py` | **New.** Generate the educator HTML review sheet(s) (image + transcript + grades + flags). |
| `app/streamlit_app.py` | **New.** Educator UI: upload questions/notes/scans, run grading, review reports + scans, download HTML. |
| `src/homosapien/schemas.py` | Small additions: transcription regions + review status on `StudentAnswer` (see below). |
| `src/homosapien/cli.py` | New subcommand `grade --scans <dir> [--review-out <dir>]`. |
| `pyproject.toml` / `requirements.txt` | Add a `vision` extra: `pymupdf`, `pillow`. |
| `tests/test_ingest.py`, `tests/test_review.py` | **New.** Deterministic tests in MOCK mode. |
| `docs/ARCHITECTURE.md` | Document the ingestion + review flow. |

### Schema additions (kept minimal)
- `TranscriptionRegion(text, confidence, kind)` — for highlighting weak reads.
- `StudentAnswer`: add `regions: list[TranscriptionRegion] = []` and
  `transcription_notes: str | None` (image path + confidence already exist).

---

## What each piece does

### 1. `vision_transcribe` (LIVE)
- Input: one image/PDF path for one question's scan.
- `image_prep`: load → (PDF? rasterize @ ~200 DPI) → resize longest side to
  Bedrock's guidance (~1568 px), compress under the size cap.
- Bedrock Converse with an image block + a transcription prompt requesting
  **JSON**: `{ steps_latex, final_expr (CAS-parseable or null), regions:[{text,
  confidence}], overall_confidence }`.
- Transcribe faithfully — **do not correct the student's maths**; emit per-region
  confidence.
- Return an enriched `Transcription`; `confidence = min(region confidences)`.

### 2. `ingest.py`
- `ingest_answer(student_id, question_id, path) -> StudentAnswer` — runs
  transcription, fills `raw_text` (LaTeX), `final_expr`, `scan_path`,
  `transcription_confidence`, `regions`.
- `ingest_dir(root) -> list[StudentAnswer]` — walks the `scans/<student>/<q>.<ext>`
  convention. Routes straight into `run_uc1` / `run_uc2` unchanged.
- CLI: `homosapien grade --scans scans/ --review-out review/`.

### 3. Educator review surface (`review.py`)
Per student, an HTML sheet with, for each question:
- the **original scan** (embedded), beside
- the **transcribed working** (raw LaTeX; optional KaTeX render later), the
  detected **final expression**, and
- the **per-criterion grades** (full/partial/zero, rationale, `[SymPy]` flags),
  with **escalations and low-confidence regions surfaced at the top**.
Plus a **cohort index** linking every student and highlighting who needs review.
Educator eyeballs scan vs transcript, confirms or overrides. Doubles as demo gold.

---

## Order of work (checklist)
- [x] 1. Deps (`pymupdf`, `pillow`, `streamlit`) + `vision`/`ui` extras; schema additions.
- [x] 2. `image_prep.py` (load, PDF rasterize, resize).
- [x] 3. `vision_transcribe` LIVE (Converse image block + structured output + min-confidence).
- [x] 4. `ingest.py` (single + directory) — unit-tested in MOCK.
- [x] 5. `review.py` HTML sheet + cohort index — unit-tested.
- [x] 6. CLI `grade --scans … --review-out …`.
- [x] 7. **Streamlit UI** (`app/streamlit_app.py`) — upload + review, verified rendering in MOCK.
- [x] 8. Mock default + typed-input fallback intact; full `pytest` green (28 passed).
- [ ] 9. **Pending you:** 3–5 real handwritten sample scans to validate the LIVE vision path.

---

## Testing
- **Deterministic (CI-safe, MOCK):** `image_prep` (resize/PDF), `ingest` over a
  temp `scans/` tree using the mock transcriber, `review` HTML generation.
- **LIVE (manual):** a few real sample scans with known ground truth; measure
  transcription accuracy and quote it alongside grading agreement.
- **I will need 3–5 sample handwritten images/PDFs from you** to validate the
  LIVE path — or I can generate typed-as-image stand-ins to prove the plumbing
  while you gather real scripts.

## Out of scope (deferred)
- Auto question-segmentation from a whole-paper scan.
- In-browser interactive override/write-back (v1 review is read-only QA).
- KaTeX/MathJax rendering polish (v1 shows raw LaTeX beside the image).
- MathPix integration (fallback only, if Claude vision math accuracy is poor).

## Risks & mitigations
- **Math-notation OCR errors** → confidence gating + escalation + the review
  sheet puts a human on every uncertain read; typed-input fallback for the demo.
- **PDF/image size limits** → `image_prep` resizes/compresses before the call.
- **Cost/latency** (one vision call per page) → cache by file hash so re-runs
  during dev don't re-pay; keep MOCK as the default.
- **Privacy** (scans are student PII) → process in your AWS account, don't retain,
  note it in the README.

## Guardrails
- Nothing is committed or staged.
- `tests/conftest.py` keeps the suite in MOCK, so tests never call Bedrock.

---

# PHASE 2 — real coursework (INF1003 discrete maths)

**Status:** proposed plan, awaiting go-ahead. Nothing built yet.
**Trigger:** the real dataset is (a) questions in a **typed tutorial PDF**, and
(b) a student's answers as **one multi-page handwritten PDF per tutorial**
(`T{n}.pdf`). Phase-1 assumed one scan = one question and pre-built `Question`
objects. Two new pieces bridge that.

**Pilot:** Topic 1 — Sequences & Summation (computational, so it also exercises
SymPy; full materials + `T1.pdf` at 3 pages).

## Domain note (sets expectations)
INF1003 is discrete maths — logic, sets, proofs, combinatorics. Most answers are
**judgement-graded**; SymPy only bites on computational topics (1, 2, 3). So on
this course the LLM grader carries most of the load and SymPy is a spot-checker,
not the main event. Topic 1 is chosen partly to keep SymPy in play.

## The two new pieces

### A. Question extraction — `tools/extract_questions.py` (new)
- `extract_from_pdf(pdf) -> list[Question]`: PyMuPDF text (extracts cleanly) →
  an LLM structuring pass → `Question(id, prompt, max_marks, type)`.
- `notes_from_pdfs(paths) -> Notes`: concatenate typed text (formula sheet +
  tutorial, optionally slides) as grading context, capped for token cost.
- MOCK returns a small canned Topic-1 question set; LIVE does the real extraction.
- Output pre-fills the UI questions editor, so the educator reviews/edits before
  grading (the editor already supports editing prompt / marks / type).

### B. Whole-paper transcription segmented by question
- `vision_transcribe.transcribe_paper(pdf, questions) -> dict[qid, Transcription]`:
  send all page images in ONE Converse call, pass the known questions, and ask
  the model to **group the student's work by question id**, with per-question
  `steps_latex`, `final_expr`, confidence, and an **attempted** flag.
- `ingest.ingest_paper(student_id, pdf, questions) -> list[StudentAnswer]`: one
  `StudentAnswer` per question from a single multi-page PDF.
- Fairness: **illegible → escalate**; **not attempted → legitimate zero** (the
  model distinguishes the two; we never escalate a blank as if it were unreadable).

## Decisions (please confirm / change)
1. **Question granularity:** grade at the **top-level numbered question** (Q1,
   Q2, …); sub-parts (a–j) live inside the prompt and are captured by the mark
   scheme's criteria. Simpler segmentation, still fair. *(Alternative: per-sub-part,
   more work + harder segmentation.)*
2. **Marks:** the tutorials state no per-question marks, so extraction **proposes**
   `max_marks` and the educator edits them in the UI before grading. OK, or do you
   have a real mark scheme to load?
3. **Notes source:** formula sheet + tutorial text by default (short, relevant);
   full slide decks are 36–48 pages so they're truncated/optional to control token
   cost. OK?
4. **Attempted vs illegible:** the vision model flags each question; blank =
   zero, unreadable = escalate.

## Flow (pilot, Topic 1)
1. `extract_from_pdf(Topic 1 tutorial)` → questions → review in UI.
2. `notes_from_pdfs(formula sheet [+ Topic 1 slides])` → notes.
3. `ingest_paper(student, T1.pdf, questions)` → per-question answers (LIVE vision).
4. `run_uc1(...)` → report → review in UI / HTML.

## Files touched
- `tools/extract_questions.py` (new), `tools/vision_transcribe.py` (+`transcribe_paper`),
  `tools/ingest.py` (+`ingest_paper`), `schemas.py` (add `attempted` to `StudentAnswer`),
  `cli.py` (`grade-tutorial --tutorial … --answer … --student …`),
  `app/streamlit_app.py` (a "whole tutorial PDF" upload mode that auto-extracts
  questions), tests for extraction + segmentation (MOCK).

## Open question for you
The current UI maps one uploaded file → one question. Phase 2 needs a **"whole
tutorial" mode**: upload the tutorial PDF (auto-extract questions) + one student's
answer PDF. Build that UI mode now, or start CLI-only and add the UI after the
pilot proves out?

## Out of scope (still deferred)
- Per-sub-part segmentation; multi-student batch over PDFs (UC2) — after the UC1
  pilot works.
