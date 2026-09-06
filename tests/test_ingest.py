"""Ingestion in MOCK mode (no Bedrock, no real image decoding)."""
import pytest

from homosapien.tools import ingest


def test_ingest_answer_builds_student_answer():
    ans = ingest.ingest_answer("alice", "Q1", "scans/alice/Q1.png")
    assert ans.student_id == "alice" and ans.question_id == "Q1"
    assert ans.raw_text and ans.final_expr        # transcription populated
    assert ans.scan_path == "scans/alice/Q1.png"
    assert 0.0 <= ans.transcription_confidence <= 1.0
    assert ans.regions                             # per-region reads present


def test_ingest_dir_walks_convention(tmp_path):
    for student in ("alice", "bob"):
        d = tmp_path / student
        d.mkdir()
        (d / "Q1.png").write_bytes(b"")   # mock transcriber never reads the bytes
    answers = ingest.ingest_dir(str(tmp_path))
    assert {a.student_id for a in answers} == {"alice", "bob"}
    assert all(a.question_id == "Q1" for a in answers)


def test_ingest_dir_empty_raises(tmp_path):
    with pytest.raises(ValueError):
        ingest.ingest_dir(str(tmp_path))
