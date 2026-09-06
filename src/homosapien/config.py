"""Runtime configuration, read once from the environment.

MOCK mode (the default) lets the whole pipeline run offline with canned model
outputs, so the deterministic parts — SymPy verification, transposition,
routing, escalation — can be exercised without any AWS setup.
"""
from __future__ import annotations

import os

try:  # optional convenience; not required
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
    pass


def _flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


LIVE: bool = _flag("HOMOSAPIEN_LIVE", "0")
MODEL_ID: str = os.getenv(
    "HOMOSAPIEN_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)
AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
CONFIDENCE_THRESHOLD: float = float(os.getenv("HOMOSAPIEN_CONF_THRESHOLD", "0.75"))


def mode() -> str:
    return "LIVE (Bedrock)" if LIVE else "MOCK (offline)"
