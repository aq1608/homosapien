# homosapien

**Grading handwritten university mathematics with human judgement — at cohort scale.**

An AI agent, built with the [Strands Agents SDK](https://strandsagents.com), that
takes a tutorial's questions and lecture notes, reads students' handwritten
working, awards **full / partial / zero** on every step *with a reason*, verifies
the mathematics deterministically, and writes each student their own report. It
runs the whole first pass unattended and interrupts the educator only for a real
decision.

> Built for the **Agents for Humans** hackathon · Professional Agents track.

---

## Why

Marking maths is slow, repetitive, and quietly unfair — the 30th script rarely
gets the same bar as the 3rd. The hard parts (partial credit, multiple valid
methods, error-carried-forward, and *consistency*) are exactly where a naïve
"AI, grade this" fails. `homosapien` is designed around them:

- **Method over answer.** Per-criterion marks (M/A), not one verdict.
- **The maths is verified, not vibed.** Accuracy marks are gated on **SymPy**, never
  the model's own arithmetic.
- **Consistency by construction.** In the many-student case it grades one question
  across the whole cohort in a batch, then reports per student.
- **Fair to handwriting.** A student is never marked down for the OCR's mistake —
  low-confidence scans are escalated, not penalised.

## Two workflows

| | Input | Output |
|---|---|---|
| **UC1** | one student, whole paper | one report for that student |
| **UC2** | many students (one question or the whole paper) | one report **per student** + cohort insights |

The router detects which automatically. The UC2 move: **grade column-major**
(consistency) → **transpose** → **report row-major** (per student).

## Quick start (offline, no AWS)

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows
# python -m venv .venv && source .venv/bin/activate  # macOS/Linux
pip install -e ".[dev]"

homosapien demo-uc1     # one student, whole paper
homosapien demo-uc2     # many students -> per-student reports + cohort insight
pytest                  # SymPy / transpose / router / end-to-end smoke tests
```

The scaffold runs in **MOCK mode** by default: language-model steps return canned
outputs so the deterministic core — **SymPy verification, transposition, routing,
escalation** — runs with no cloud setup. The SymPy checks are real: in the demo,
one student's correct integral earns a verified full mark while another's wrong
final answer loses it.

## Going live (Amazon Bedrock)

```bash
cp .env.example .env      # set HOMOSAPIEN_LIVE=1, model id, AWS_REGION
# enable Bedrock model access in the AWS console; configure AWS credentials
homosapien demo-uc1
```

All model coupling lives in [`src/homosapien/llm.py`](src/homosapien/llm.py).

## Educator UI

A Streamlit app to upload questions, notes, and student scans, then review each
student's report beside the original scan (colour-coded marks, `[SymPy]`-verified
accuracy, escalations surfaced, downloadable HTML review sheet).

```bash
pip install -e ".[ui]"
streamlit run app/streamlit_app.py
```

Click **Load sample cohort** to see the full flow with no files. Runs in MOCK
with no AWS; set `HOMOSAPIEN_LIVE=1` for real Bedrock grading + handwriting
transcription.

## Grade real scans (CLI)

Lay scans out as `scans/<student_id>/<question_id>.<ext>` (PNG / JPG / PDF):

```bash
pip install -e ".[vision]"
homosapien grade --scans scans/ --review-out review.html
```

`vision_transcribe` reads each scan with Claude vision on Bedrock (needs
`HOMOSAPIEN_LIVE=1`). Per the fairness rule, a low-legibility scan is **escalated**
for human review, never silently penalised.

## Deploy to AgentCore

```bash
pip install -e ".[agentcore]"
agentcore configure -e agentcore/app.py
agentcore launch
```

See [`agentcore/app.py`](agentcore/app.py).

## Layout

```
src/homosapien/
  router.py          workflow detection (UC1/UC2) + grader dispatch
  schemas.py         typed data model (pydantic)
  llm.py             single point of model contact (mock ↔ Bedrock)
  agent.py           Strands orchestrator (agent-driven path)
  fixtures.py        demo data (a calculus Q + a proof)
  tools/
    sympy_verify.py    ✅ deterministic maths verification (the trust anchor)
    transpose.py       ✅ column-major ↔ row-major pivot (UC2)
    escalation.py      ✅ what gets handed back to the educator
    scheme_builder.py  mark scheme: provided OR drafted → approved
    grader.py          per-criterion grading; accuracy marks gated on SymPy
    report_writer.py   per-student narrative report
    cohort_insights.py shared errors worth reteaching (UC2)
    vision_transcribe.py  handwriting → LaTeX (LIVE = TODO week-3)
  workflows/
    uc1_single_student.py
    uc2_many_students.py
agentcore/app.py     Bedrock AgentCore Runtime entrypoint
tests/               sympy · transpose · router · end-to-end smoke
docs/ARCHITECTURE.md
```

## Status

Implemented and tested: SymPy verification, transpose, router, escalation,
schemas, and both workflows end-to-end in MOCK mode. To wire next: LIVE Bedrock
calls for the judgement-heavy sub-agents, and the Bedrock **vision** transcription
for real handwritten scans (`TODO(week-3)`). See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full picture and the build
plan.

## License

[MIT](LICENSE).

*Note: student scripts are personal data. Keep processing in your own AWS
account, don't retain beyond the task, and position this as a co-pilot — the
educator remains the final authority on every mark.*
