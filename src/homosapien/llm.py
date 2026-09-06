"""Single point of contact with the language model.

Every judgement-heavy sub-agent (scheme_builder, grader, report_writer,
cohort_insights) goes through :func:`run_structured`. In MOCK mode it returns
the supplied canned result so the pipeline runs offline; in LIVE mode it builds
a focused Strands ``Agent`` on Amazon Bedrock and parses its JSON reply into the
requested Pydantic model.

Keeping all model coupling here means the rest of the codebase is plain,
testable Python.
"""
from __future__ import annotations

import json
import re
from typing import Callable, TypeVar

from pydantic import BaseModel

from . import config

T = TypeVar("T", bound=BaseModel)


def run_structured(
    system_prompt: str,
    user_prompt: str,
    response_model: type[T],
    mock: Callable[[], T],
) -> T:
    """Return a ``response_model`` instance from the model, or the mock offline.

    Parameters
    ----------
    mock:
        Zero-arg callable producing a canned ``response_model`` — used in MOCK
        mode and as a safety net. Design your mocks to reflect the inputs so the
        offline pipeline stays representative.
    """
    if not config.LIVE:
        return mock()

    try:
        from strands import Agent
        from strands.models import BedrockModel
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "LIVE mode needs the Strands SDK: pip install strands-agents"
        ) from exc

    agent = Agent(
        model=BedrockModel(model_id=config.MODEL_ID),
        system_prompt=system_prompt,
        callback_handler=None,  # silence the SDK's streaming stdout print
    )
    schema = json.dumps(response_model.model_json_schema())
    prompt = (
        f"{user_prompt}\n\n"
        f"Respond with ONLY valid JSON matching this schema:\n{schema}"
    )
    result = agent(prompt)
    text = _message_text(result)
    data = _extract_json(text)
    return response_model.model_validate(data)


def _message_text(result: object) -> str:
    """Pull plain text out of a Strands result, defensively."""
    msg = getattr(result, "message", result)
    if isinstance(msg, dict):
        # Bedrock content-block shape: {"content": [{"text": "..."}]}
        content = msg.get("content", msg)
        if isinstance(content, list):
            return "".join(
                block.get("text", "") for block in content if isinstance(block, dict)
            )
        return str(content)
    return str(msg)


def _extract_json(text: str) -> dict:
    """Best-effort JSON extraction from a model reply."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError(f"No JSON object found in model reply: {text[:200]!r}")
