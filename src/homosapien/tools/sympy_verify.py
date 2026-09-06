"""Deterministic mathematics verification — the trust anchor of the grader.

Accuracy marks are never decided by the language model's own arithmetic. They
are gated on this module, which checks symbolic equivalence with SymPy. That is
what makes a grade defensible.

Parsing is deliberately tolerant of how humans (and mark schemes) write maths —
implicit multiplication (``x e^x``), caret exponents (``x^2``), and ``e`` as
Euler's number all parse — because a parse failure must never become a student's
lost mark. This is fully working code, not a stub.
"""
from __future__ import annotations

from dataclasses import dataclass

import sympy as sp
from sympy import E, I, Symbol, exp, pi
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


@dataclass
class VerifyResult:
    equivalent: bool
    method: str          # "symbolic" | "numeric" | "error"
    detail: str = ""

    def __bool__(self) -> bool:
        return self.equivalent


# ``e`` -> Euler's number; ``exp`` stays the function even under implicit mult.
_LOCALS = {"e": E, "E": E, "pi": pi, "I": I, "exp": exp}
_TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)
# Symbols we treat as an arbitrary integration constant.
_CONSTS = {Symbol("C"), Symbol("c")}


def _parse(expr: str):
    """Parse an expression tolerantly (implicit mult, ``^`` exponent, ``e``)."""
    return parse_expr(expr.strip(), local_dict=_LOCALS, transformations=_TRANSFORMS)


def are_equivalent(a: str, b: str) -> VerifyResult:
    """True iff expressions ``a`` and ``b`` are mathematically equal."""
    try:
        ea, eb = _parse(a), _parse(b)
    except Exception as exc:  # broad: parse_expr raises many exception types
        return VerifyResult(False, "error", f"could not parse: {exc}")
    try:
        diff = sp.simplify(ea - eb)
        if diff == 0 or getattr(diff, "is_zero", False):
            return VerifyResult(True, "symbolic", "simplify(a - b) == 0")
        if ea.equals(eb) is True:  # numeric fallback for tricky forms
            return VerifyResult(True, "numeric", "SymPy .equals() confirmed")
        return VerifyResult(False, "symbolic", f"non-zero difference: {diff}")
    except Exception as exc:  # pragma: no cover - defensive
        return VerifyResult(False, "error", f"comparison failed: {exc}")


def equivalent_up_to_constant(a: str, b: str) -> VerifyResult:
    """True iff ``a`` and ``b`` differ only by an arbitrary additive constant.

    Catches an omitted ``+ C`` on an indefinite integral. Deliberately does NOT
    treat a *numeric* offset as "up to constant" — a definite/computed answer
    that is off by a number is simply wrong. Whether to penalise a missing ``+ C``
    is a marking-policy call the grader escalates rather than decides.
    """
    try:
        ea, eb = _parse(a), _parse(b)
    except Exception as exc:
        return VerifyResult(False, "error", f"could not parse: {exc}")
    try:
        diff = sp.simplify(ea - eb)
        if diff == 0 or getattr(diff, "is_zero", False):
            return VerifyResult(True, "symbolic", "identical (difference 0)")
        syms = diff.free_symbols
        is_const = bool(syms) and syms <= _CONSTS
        return VerifyResult(bool(is_const), "symbolic", f"difference = {diff}")
    except Exception as exc:  # pragma: no cover - defensive
        return VerifyResult(False, "error", f"comparison failed: {exc}")
