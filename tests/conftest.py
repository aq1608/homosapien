"""Test hermeticity: force MOCK mode before any homosapien module is imported.

Without this, a developer's ``.env`` with ``HOMOSAPIEN_LIVE=1`` would make the
grading tests fire real Bedrock calls (slow, costs money, non-deterministic).
This runs at collection time, before ``homosapien.config`` reads the environment,
and ``load_dotenv(override=False)`` will not overwrite it.
"""
import os

os.environ["HOMOSAPIEN_LIVE"] = "0"
