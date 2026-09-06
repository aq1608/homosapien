"""Command-line entry point.

    homosapien demo-uc1     # one student, whole paper -> one report
    homosapien demo-uc2     # many students -> per-student reports + cohort insight
    homosapien version

Runs in MOCK mode by default (no AWS needed). Set HOMOSAPIEN_LIVE=1 for Bedrock.
"""
from __future__ import annotations

import argparse

from . import __version__, config, fixtures
from .router import detect_workflow
from .schemas import StudentReport
from .workflows import run_uc1, run_uc2


def _print_report(r: StudentReport) -> None:
    print(f"\n─── Report · {r.student_id} · {r.total_awarded}/{r.total_max} ───")
    print(r.narrative)
    for g in r.per_question:
        flag = "  ⚠ ESCALATED" if g.escalate else ""
        print(f"  {g.question_id}: {g.marks_awarded}/{g.max_marks}{flag}")
        for cg in g.criteria:
            chk = " [SymPy]" if cg.sympy_checked else ""
            print(f"      {cg.criterion_id} {cg.level.value:<7} {cg.marks_awarded}m{chk} — {cg.rationale}")
        for reason in g.escalation_reasons:
            print(f"      ↳ escalate: {reason}")


def demo_uc1() -> None:
    answers = fixtures.single_student_answers()
    print(f"[mode: {config.mode()}]  workflow detected: {detect_workflow(answers)}")
    report = run_uc1(fixtures.QUESTIONS, fixtures.NOTES, answers)
    _print_report(report)


def demo_uc2() -> None:
    answers = fixtures.cohort_answers()
    print(f"[mode: {config.mode()}]  workflow detected: {detect_workflow(answers)}")
    reports, insights = run_uc2(fixtures.QUESTIONS, fixtures.NOTES, answers)
    for r in reports:
        _print_report(r)
    print("\n─── Cohort insights ───")
    if not insights:
        print("  (none crossed the reteach threshold)")
    for ins in insights:
        print(f"  • {ins.observation}")


def grade_scans(scans_dir: str, review_out: str | None) -> None:
    from .tools import ingest, review

    answers = ingest.ingest_dir(scans_dir)
    workflow = detect_workflow(answers)
    print(f"[mode: {config.mode()}]  workflow detected: {workflow}  "
          f"({len({a.student_id for a in answers})} student(s))")
    if workflow == "UC1":
        reports = [run_uc1(fixtures.QUESTIONS, fixtures.NOTES, answers)]
    else:
        reports, insights = run_uc2(fixtures.QUESTIONS, fixtures.NOTES, answers)
        for ins in insights:
            print(f"  • {ins.observation}")
    for r in reports:
        _print_report(r)
    if review_out:
        html = review.build_html(reports, answers)
        with open(review_out, "w", encoding="utf-8") as fh:
            fh.write(html)
        print(f"\nReview sheet written to {review_out}")


def grade_tutorial(tutorial: str, answer: str, student: str,
                   notes_pdfs: list[str] | None, review_out: str | None) -> None:
    from .schemas import Notes
    from .tools import extract_questions, ingest, review

    questions = extract_questions.extract_from_pdf(tutorial)
    notes = (extract_questions.notes_from_pdfs(notes_pdfs)
             if notes_pdfs else Notes(text=extract_questions._pdf_text(tutorial)))
    answers = ingest.ingest_paper(student, answer, questions)
    print(f"[mode: {config.mode()}]  {len(questions)} question(s) extracted; "
          f"grading {student}")
    report = run_uc1(questions, notes, answers)
    _print_report(report)
    if review_out:
        with open(review_out, "w", encoding="utf-8") as fh:
            fh.write(review.build_html([report], answers))
        print(f"\nReview sheet written to {review_out}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="homosapien", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo-uc1", help="one student, whole paper")
    sub.add_parser("demo-uc2", help="many students -> per-student reports")
    g = sub.add_parser("grade", help="grade a scans/<student>/<question>.<ext> tree")
    g.add_argument("--scans", required=True, help="path to the scans directory")
    g.add_argument("--review-out", help="write a self-contained HTML review sheet here")
    t = sub.add_parser("grade-tutorial", help="grade one handwritten tutorial PDF")
    t.add_argument("--tutorial", required=True, help="typed tutorial PDF (questions)")
    t.add_argument("--answer", required=True, help="student's handwritten answer PDF")
    t.add_argument("--student", default="student", help="student id")
    t.add_argument("--notes", nargs="*", help="context PDFs (formula sheet, slides)")
    t.add_argument("--review-out", help="write a self-contained HTML review sheet here")
    sub.add_parser("version", help="print version")

    args = parser.parse_args()
    if args.command == "demo-uc1":
        demo_uc1()
    elif args.command == "demo-uc2":
        demo_uc2()
    elif args.command == "grade":
        grade_scans(args.scans, args.review_out)
    elif args.command == "grade-tutorial":
        grade_tutorial(args.tutorial, args.answer, args.student, args.notes, args.review_out)
    elif args.command == "version":
        print(f"homosapien {__version__}")


if __name__ == "__main__":
    main()
