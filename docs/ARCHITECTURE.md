# Architecture

`homosapien` grades handwritten university mathematics with human judgement, then
writes each student their own report. Two use cases, one shared brain.

## Flow

```
Ingest (scan → LaTeX)      vision_transcribe   [confidence-gated, fairness rule]
      │
      ▼
Mark scheme                scheme_builder      [provided OR drafted → approved]
      │
      ▼
Grade (per criterion)      grader              [dispatch: computational / proof]
      │  ├─ accuracy marks GATED on ───────►   sympy_verify   (deterministic)
      │  └─ borderline / policy / illegible ►  escalation     (hand back to human)
      ▼
Report                     report_writer       [per student]
Cohort patterns (UC2)      cohort_insights     [shared errors to reteach]
```

## Two workflows (the router)

- **UC1** — one student, whole paper → `workflows/uc1_single_student.py` → one report.
- **UC2** — many students → `workflows/uc2_many_students.py`:
  - **grade column-major** (all students on one question) for a consistent bar;
  - **transpose** (`tools/transpose.py`) → **report row-major**, per student;
  - plus cohort insights, cheap because grading already saw the whole column.

`router.detect_workflow` picks UC1/UC2 from the input; `router.dispatch_grader`
picks the computational (SymPy) or proof (logical-validity) path per question.

## Why explicit orchestration, not an autonomous agent loop

Grading must be reproducible and auditable, so the control flow lives in plain
Python (`workflows/`). The Strands `Agent` still powers each judgement-heavy
*step* (scheme drafting, grading proposal, report writing) via `llm.run_structured`.
`agent.py` additionally exposes an agent-driven path for conversational use.

## The trust anchor

Accuracy marks are **never** decided by the model's own arithmetic. They are
gated on `sympy_verify.are_equivalent`, which checks symbolic equivalence. This
is what makes a grade defensible — and it is real, tested code, not a stub.

## The fairness rule

A student is never marked down for the OCR's mistake. When transcription
confidence is low, `escalation.evaluate` flags the page for the educator instead
of converting uncertainty into a lost mark.

## Deployment

`agentcore/app.py` wraps the workflows in a Bedrock AgentCore Runtime entrypoint.
SymPy verification is a natural fit for AgentCore's Code Interpreter.

## Mock vs live

MOCK mode (default) returns canned model outputs so the deterministic core —
SymPy, transpose, router, escalation — runs offline with no AWS. Set
`HOMOSAPIEN_LIVE=1` to call Bedrock. All model coupling lives in `llm.py`.

## Status

| Component | State |
|---|---|
| `sympy_verify`, `transpose`, `router`, `escalation`, `schemas` | ✅ implemented + tested |
| `workflows` UC1 / UC2, `cli`, `fixtures` | ✅ runnable in MOCK mode |
| `scheme_builder`, `grader`, `report_writer`, `cohort_insights` | ✅ real prompts, mock outputs; wire LIVE |
| `vision_transcribe` LIVE | ⏳ TODO(week-3): Bedrock vision |
| `agentcore/app.py` | ✅ scaffolded; deploy to validate |
