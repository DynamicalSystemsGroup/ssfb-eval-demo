"""Tests for evaluation.py — EvaluationLayer post-hoc scoring and DataFrame.

Uses fixture trajectory JSONs and stub questions written to tmp_path.
No ontology or Ollama needed.
"""

import json
import math

import pandas as pd
import pytest

from apollo_eval.ontology import ScoreResult
from apollo_eval.evaluation import EvaluationLayer


# --- Stubs ---

class _StubQuestion:
    """Question that scores based on whether response contains 'yes'."""

    def __init__(self, question_id: str):
        self.question_id = question_id
        self.prompt = f"prompt for {question_id}"

    def score(self, response: str) -> ScoreResult:
        if "yes" in response.lower():
            return ScoreResult(question_id=self.question_id, parse_success=True, score=1.0, fuzz=False)
        elif "no" in response.lower():
            return ScoreResult(question_id=self.question_id, parse_success=True, score=0.0, fuzz=False)
        else:
            return ScoreResult(question_id=self.question_id, parse_success=False, score=0.0, fuzz=None)


class _FuzzyQuestion:
    """Question that always returns fuzz=True."""

    def __init__(self, question_id: str):
        self.question_id = question_id
        self.prompt = f"prompt for {question_id}"

    def score(self, response: str) -> ScoreResult:
        return ScoreResult(question_id=self.question_id, parse_success=True, score=1.0, fuzz=True)


def _write_trajectory(path, run_id, seed, turns):
    """Write a trajectory JSON file."""
    data = {
        "run_id": run_id,
        "seed": seed,
        "scenario_iri": "http://example.org/test",
        "turns": turns,
    }
    filepath = path / f"{run_id}.json"
    filepath.write_text(json.dumps(data))
    return filepath


# --- Tests ---

class TestLoadTrajectories:
    # Req: loads all trajectory JSON files from directory
    def test_load_trajectories(self, tmp_path):
        _write_trajectory(tmp_path, "run-1", 0, [{"position_index": 0, "question_id": "q1", "u": "p", "y": "yes", "parse_success": True, "score": 1.0}])
        _write_trajectory(tmp_path, "run-2", 1, [{"position_index": 0, "question_id": "q1", "u": "p", "y": "no", "parse_success": True, "score": 0.0}])
        evaluator = EvaluationLayer(str(tmp_path), [_StubQuestion("q1")])
        trajectories = evaluator.load_trajectories()
        assert len(trajectories) == 2

    # Req: empty directory returns empty list
    def test_load_empty_directory(self, tmp_path):
        evaluator = EvaluationLayer(str(tmp_path), [_StubQuestion("q1")])
        assert evaluator.load_trajectories() == []


class TestBuildDataFrame:
    # Req: DataFrame has correct columns
    def test_columns(self, tmp_path):
        _write_trajectory(tmp_path, "run-1", 0, [
            {"position_index": 0, "question_id": "q1", "u": "p", "y": "yes", "parse_success": True, "score": 1.0},
        ])
        evaluator = EvaluationLayer(str(tmp_path), [_StubQuestion("q1")])
        df = evaluator.build_dataframe()
        assert set(df.columns) == {"question_id", "run_id", "position_index", "parse_success", "score", "fuzz"}

    # Req: score is NaN when parse_success is False — not 0.0
    def test_parse_failure_nan(self, tmp_path):
        _write_trajectory(tmp_path, "run-1", 0, [
            {"position_index": 0, "question_id": "q1", "u": "p", "y": "gibberish", "parse_success": False, "score": None},
        ])
        evaluator = EvaluationLayer(str(tmp_path), [_StubQuestion("q1")])
        df = evaluator.build_dataframe()
        row = df.iloc[0]
        assert row["parse_success"] == False
        assert math.isnan(row["score"])

    # Req: re-scores from response text, not stored score
    def test_rescores_from_response(self, tmp_path):
        # Store a wrong score in JSON (1.0) but response says "no" → re-score should give 0.0
        _write_trajectory(tmp_path, "run-1", 0, [
            {"position_index": 0, "question_id": "q1", "u": "p", "y": "no way", "parse_success": True, "score": 1.0},
        ])
        evaluator = EvaluationLayer(str(tmp_path), [_StubQuestion("q1")])
        df = evaluator.build_dataframe()
        assert df.iloc[0]["score"] == 0.0  # re-scored, not the stored 1.0

    # Req: fuzz column populated from ScoreResult
    def test_fuzz_column(self, tmp_path):
        _write_trajectory(tmp_path, "run-1", 0, [
            {"position_index": 0, "question_id": "q1", "u": "p", "y": "yes exact", "parse_success": True, "score": 1.0},
        ])
        evaluator = EvaluationLayer(str(tmp_path), [_FuzzyQuestion("q1")])
        df = evaluator.build_dataframe()
        assert df.iloc[0]["fuzz"] == True

    # Req: fuzz is NaN when parse fails
    def test_fuzz_nan_on_parse_failure(self, tmp_path):
        _write_trajectory(tmp_path, "run-1", 0, [
            {"position_index": 0, "question_id": "q1", "u": "p", "y": "gibberish", "parse_success": False, "score": None},
        ])
        evaluator = EvaluationLayer(str(tmp_path), [_StubQuestion("q1")])
        df = evaluator.build_dataframe()
        assert pd.isna(df.iloc[0]["fuzz"])

    # Req: multiple runs and turns build correct DataFrame
    def test_multiple_runs(self, tmp_path):
        _write_trajectory(tmp_path, "run-1", 0, [
            {"position_index": 0, "question_id": "q1", "u": "p", "y": "yes", "parse_success": True, "score": 1.0},
            {"position_index": 1, "question_id": "q2", "u": "p", "y": "no", "parse_success": True, "score": 0.0},
        ])
        _write_trajectory(tmp_path, "run-2", 1, [
            {"position_index": 0, "question_id": "q1", "u": "p", "y": "yes", "parse_success": True, "score": 1.0},
            {"position_index": 1, "question_id": "q2", "u": "p", "y": "yes", "parse_success": True, "score": 1.0},
        ])
        evaluator = EvaluationLayer(str(tmp_path), [_StubQuestion("q1"), _StubQuestion("q2")])
        df = evaluator.build_dataframe()
        assert len(df) == 4
        assert set(df["run_id"]) == {"run-1", "run-2"}


class TestSummaries:
    @pytest.fixture
    def eval_df(self, tmp_path):
        """Two runs, two questions, one parse failure."""
        _write_trajectory(tmp_path, "run-1", 0, [
            {"position_index": 0, "question_id": "q1", "u": "p", "y": "yes", "parse_success": True, "score": 1.0},
            {"position_index": 1, "question_id": "q2", "u": "p", "y": "no", "parse_success": True, "score": 0.0},
        ])
        _write_trajectory(tmp_path, "run-2", 1, [
            {"position_index": 0, "question_id": "q1", "u": "p", "y": "yes", "parse_success": True, "score": 1.0},
            {"position_index": 1, "question_id": "q2", "u": "p", "y": "gibberish", "parse_success": False, "score": None},
        ])
        evaluator = EvaluationLayer(str(tmp_path), [_StubQuestion("q1"), _StubQuestion("q2")])
        return evaluator, evaluator.build_dataframe()

    # Req: summary_by_question groups by question_id
    def test_summary_by_question(self, eval_df):
        evaluator, df = eval_df
        summary = evaluator.summary_by_question(df)
        assert "q1" in summary.index.values
        assert "q2" in summary.index.values
        # q1: 1.0 in both runs → mean 1.0
        assert summary.loc["q1", "score"] == 1.0

    # Req: summary_by_position groups by position_index
    def test_summary_by_position(self, eval_df):
        evaluator, df = eval_df
        summary = evaluator.summary_by_position(df)
        assert 0 in summary.index.values
        assert 1 in summary.index.values

    # Req: summary_by_run groups by run_id
    def test_summary_by_run(self, eval_df):
        evaluator, df = eval_df
        summary = evaluator.summary_by_run(df)
        assert "run-1" in summary.index.values
        assert "run-2" in summary.index.values

    # Req: NaN scores excluded from mean (parse failures don't contaminate)
    def test_nan_excluded_from_mean(self, eval_df):
        evaluator, df = eval_df
        summary = evaluator.summary_by_question(df)
        # q2: run-1 score=0.0, run-2 parse_failure=NaN → mean should be 0.0 (not 0.0+NaN/2)
        assert summary.loc["q2", "score"] == 0.0
