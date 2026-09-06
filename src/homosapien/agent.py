"""Strands orchestrator — the agent-driven alternative to the explicit workflows.

The ``workflows`` package is the primary, deterministic path (reproducible,
auditable grading). This module shows the same capabilities exposed to a Strands
``Agent`` as ``@tool`` functions, for conversational / exploratory use. Both
share the underlying tool implementations.
"""
from __future__ import annotations

from strands import Agent, tool
from strands.models import BedrockModel

from . import config
from .tools.sympy_verify import are_equivalent

ORCHESTRATOR_PROMPT = """You are homosapien, a mathematics grading assistant.
You grade university tutorials fairly and consistently: method over answer,
partial credit, error carried forward. You NEVER verify arithmetic yourself —
always call `verify_equivalence` for that. You escalate borderline or
policy-dependent calls to the educator rather than deciding them.
"""


@tool
def verify_equivalence(expr_a: str, expr_b: str) -> str:
    """Check whether two mathematical expressions are equal, using SymPy.

    Use this for every accuracy judgement instead of computing by hand.
    Returns a short verdict string.
    """
    result = are_equivalent(expr_a, expr_b)
    verdict = "EQUIVALENT" if result.equivalent else "NOT equivalent"
    return f"{verdict} ({result.method}): {result.detail}"


def build_orchestrator() -> Agent:
    """Construct the Strands orchestrator agent (requires Bedrock access)."""
    return Agent(
        model=BedrockModel(model_id=config.MODEL_ID),
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[verify_equivalence],
        callback_handler=None,  # silence the SDK's streaming stdout print
    )
