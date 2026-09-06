"""Amazon Bedrock AgentCore Runtime entry point.

Deploy with the AgentCore starter toolkit:

    pip install -e ".[agentcore]"
    agentcore configure -e agentcore/app.py
    agentcore launch

The SymPy verifier is a natural fit for AgentCore's Code Interpreter; for the
scaffold it runs in-process. Payload shape:

    {"workflow": "uc1" | "uc2"}   # uses the bundled fixtures for a smoke test

Extend the entrypoint to accept real questions/notes/answers as JSON.
"""
from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from homosapien import fixtures
from homosapien.workflows import run_uc1, run_uc2

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):  # noqa: ANN001
    workflow = (payload or {}).get("workflow", "uc1")
    if workflow == "uc2":
        reports, insights = run_uc2(
            fixtures.QUESTIONS, fixtures.NOTES, fixtures.cohort_answers()
        )
        return {
            "reports": [r.model_dump() for r in reports],
            "cohort_insights": [i.model_dump() for i in insights],
        }
    report = run_uc1(
        fixtures.QUESTIONS, fixtures.NOTES, fixtures.single_student_answers()
    )
    return {"report": report.model_dump()}


if __name__ == "__main__":
    app.run()
