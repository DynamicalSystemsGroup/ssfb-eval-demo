import json
import os

import pytest

from apollo_eval.utils import lookup


def _write_trajectory(tmp_path, run_id, turns):
    """Write a minimal trajectory JSON fixture."""
    data = {
        "run_id": run_id,
        "seed": 42,
        "scenario_iri": "http://example.org/scenario/1",
        "turns": turns,
    }
    path = tmp_path / f"{run_id}.json"
    path.write_text(json.dumps(data))
    return path


class TestLookup:
    # Req: lookup(run_id, position_index, trajectory_dir) returns the turn record
    def test_returns_correct_turn(self, tmp_path):
        turns = [
            {"position_index": 0, "question_id": "q-001", "u": "prompt0", "y": "resp0", "parse_success": True, "score": 1.0},
            {"position_index": 1, "question_id": "q-002", "u": "prompt1", "y": "resp1", "parse_success": False, "score": None},
        ]
        _write_trajectory(tmp_path, "run-abc", turns)
        turn = lookup("run-abc", 0, str(tmp_path))
        assert turn["question_id"] == "q-001"
        assert turn["u"] == "prompt0"

    # Req: lookup returns the correct turn when position_index is not the first
    def test_returns_second_turn(self, tmp_path):
        turns = [
            {"position_index": 0, "question_id": "q-001", "u": "p0", "y": "r0", "parse_success": True, "score": 1.0},
            {"position_index": 1, "question_id": "q-002", "u": "p1", "y": "r1", "parse_success": True, "score": 0.0},
        ]
        _write_trajectory(tmp_path, "run-xyz", turns)
        turn = lookup("run-xyz", 1, str(tmp_path))
        assert turn["question_id"] == "q-002"
        assert turn["score"] == 0.0

    # Req: score is null in JSON when parse_success is false
    def test_null_score_for_parse_failure(self, tmp_path):
        turns = [
            {"position_index": 0, "question_id": "q-001", "u": "p", "y": "r", "parse_success": False, "score": None},
        ]
        _write_trajectory(tmp_path, "run-null", turns)
        turn = lookup("run-null", 0, str(tmp_path))
        assert turn["parse_success"] is False
        assert turn["score"] is None

    # Req: lookup raises KeyError for missing position_index
    def test_raises_on_missing_position(self, tmp_path):
        turns = [
            {"position_index": 0, "question_id": "q-001", "u": "p", "y": "r", "parse_success": True, "score": 1.0},
        ]
        _write_trajectory(tmp_path, "run-miss", turns)
        with pytest.raises(KeyError):
            lookup("run-miss", 99, str(tmp_path))

    # Req: lookup raises FileNotFoundError for missing run_id
    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            lookup("nonexistent", 0, str(tmp_path))
