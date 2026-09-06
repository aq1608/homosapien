"""End-to-end orchestration for the two use cases.

These are deliberately explicit, deterministic pipelines (not "let the LLM
decide the control flow") so grading is reproducible and auditable. The Strands
Agent still powers each judgement-heavy *step*; the orchestration around them is
plain code.
"""
from .uc1_single_student import run as run_uc1
from .uc2_many_students import run as run_uc2

__all__ = ["run_uc1", "run_uc2"]
