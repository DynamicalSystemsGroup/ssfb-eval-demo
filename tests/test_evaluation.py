"""Tests for evaluation.py — EvaluationLayer post-hoc scoring and DataFrame.

Uses fixture trajectory JSONs and typed stub questions written to tmp_path.
No ontology or Ollama needed.
"""

import json
import math

import pandas as pd
import pytest

from apollo_eval.ontology import ScoreResult
from apollo_eval.evaluation import EvaluationLayer, question_type
from apollo_eval.question import (
    ClassMembershipQuestion,
    PropertyRestrictionQuestion,
    DisjointnessQuestion,
)


# --- Typed stubs (inherit from real classes so isinstance works) ---

class _StubCM(ClassMembershipQuestion):
    """CM question that scores based on whether response contains 'yes'."""
    def __init__(self, question_id: str):
        self.question_id = question_id
        self.prompt = f"prompt for {question_id}"
    def score(self, response: str) -> ScoreResult:
        if "yes" in response.lower():
            return ScoreResult(question_id=self.question_id, parse_success=True, score=1.0, fuzz=False)
        elif "no" in response.lower():
            return ScoreResult(question_id=self.question_id, parse_success=True, score=0.0, fuzz=False)
        return ScoreResult(question_id=self.question_id, parse_success=False, score=0.0, fuzz=None)


class _StubPR(PropertyRestrictionQuestion):
    """PR question — always parses, score=1.0."""
    def __init__(self, question_id: str):
        self.question_id = question_id
        self.prompt = f"prompt for {question_id}"
    def score(self, response: str) -> ScoreResult:
        if "yes" in response.lower():
            return ScoreResult(question_id=self.question_id, parse_success=True, score=1.0, fuzz=False)
        elif "no" in response.lower():
            return ScoreResult(question_id=self.question_id, parse_success=True, score=0.0, fuzz=False)
        return ScoreResult(question_id=self.question_id, parse_success=False, score=0.0, fuzz=None)


class _StubDJ(DisjointnessQuestion):
    """DJ question — always parses, score=1.0."""
    def __init__(self, question_id: str):
        self.question_id = question_id
        self.prompt = f"prompt for {question_id}"
    def score(self, response: str) -> ScoreResult:
        if "yes" in response.lower():
            return ScoreResult(question_id=self.question_id, parse_success=True, score=1.0, fuzz=False)
        elif "no" in response.lower():
            return ScoreResult(question_id=self.question_id, parse_success=True, score=0.0, fuzz=False)
        return ScoreResult(question_id=self.question_id, parse_success=False, score=0.0, fuzz=None)


class _FuzzyCM(ClassMembershipQuestion):
    """CM question that always returns fuzz=True."""
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


# --- question_type() tests ---

class TestQuestionType:
    # Req: question_type returns correct code for each subclass
    def test_cm(self):
        assert question_type(_StubCM("q1")) == "CM"

    def test_pr(self):
        assert question_type(_StubPR("q1")) == "PR"

    def test_dj(self):
        assert question_type(_StubDJ("q1")) == "DJ"


# --- Load tests ---

class TestLoadTrajectories:
    # Req: loads all trajectory JSON files from directory
    def test_load_trajectories(self, tmp_path):
        _write_trajectory(tmp_path, "run-1", 0, [{"position_index": 0, "question_id": "q1", "u": "p", "y": "yes", "parse_success": True, "score": 1.0}])
        _write_trajectory(tmp_path, "run-2", 1, [{"position_index": 0, "question_id": "q1", "u": "p", "y": "no", "parse_success": True, "score": 0.0}])
        evaluator = EvaluationLayer(str(tmp_path), [_StubCM("q1")])
        trajectories = evaluator.load_trajectories()
        assert len(trajectories) == 2

    # Req: empty directory returns empty list
    def test_load_empty_directory(self, tmp_path):
        evaluator = EvaluationLayer(str(tmp_path), [_StubCM("q1")])
        assert evaluator.load_trajectories() == []


# --- DataFrame tests ---

class TestBuildDataFrame:
    # Req: DataFrame has correct columns including question_type
    def test_columns(self, tmp_path):
        _write_trajectory(tmp_path, "run-1", 0, [
            {"position_index": 0, "question_id": "q1", "u": "p", "y": "yes", "parse_success": True, "score": 1.0},
        ])
        evaluator = EvaluationLayer(str(tmp_path), [_StubCM("q1")])
        df = evaluator.build_dataframe()
        assert set(df.columns) == {"question_id", "question_type", "run_id", "position_index", "parse_success", "score", "fuzz"}

    # Req: question_type column has correct values
    def test_question_type_column(self, tmp_path):
        _write_trajectory(tmp_path, "run-1", 0, [
            {"position_index": 0, "question_id": "q-cm", "u": "p", "y": "yes", "parse_success": True, "score": 1.0},
            {"position_index": 1, "question_id": "q-pr", "u": "p", "y": "yes", "parse_success": True, "score": 1.0},
            {"position_index": 2, "question_id": "q-dj", "u": "p", "y": "yes", "parse_success": True, "score": 1.0},
        ])
        evaluator = EvaluationLayer(str(tmp_path), [_StubCM("q-cm"), _StubPR("q-pr"), _StubDJ("q-dj")])
        df = evaluator.build_dataframe()
        assert df[df["question_id"] == "q-cm"].iloc[0]["question_type"] == "CM"
        assert df[df["question_id"] == "q-pr"].iloc[0]["question_type"] == "PR"
        assert df[df["question_id"] == "q-dj"].iloc[0]["question_type"] == "DJ"

    # Req: score is NaN when parse_success is False — not 0.0
    def test_parse_failure_nan(self, tmp_path):
        _write_trajectory(tmp_path, "run-1", 0, [
            {"position_index": 0, "question_id": "q1", "u": "p", "y": "gibberish", "parse_success": False, "score": None},
        ])
        evaluator = EvaluationLayer(str(tmp_path), [_StubCM("q1")])
        df = evaluator.build_dataframe()
        row = df.iloc[0]
        assert row["parse_success"] == False
        assert math.isnan(row["score"])

    # Req: re-scores from response text, not stored score
    def test_rescores_from_response(self, tmp_path):
        _write_trajectory(tmp_path, "run-1", 0, [
            {"position_index": 0, "question_id": "q1", "u": "p", "y": "no way", "parse_success": True, "score": 1.0},
        ])
        evaluator = EvaluationLayer(str(tmp_path), [_StubCM("q1")])
        df = evaluator.build_dataframe()
        assert df.iloc[0]["score"] == 0.0

    # Req: fuzz column populated from ScoreResult
    def test_fuzz_column(self, tmp_path):
        _write_trajectory(tmp_path, "run-1", 0, [
            {"position_index": 0, "question_id": "q1", "u": "p", "y": "yes exact", "parse_success": True, "score": 1.0},
        ])
        evaluator = EvaluationLayer(str(tmp_path), [_FuzzyCM("q1")])
        df = evaluator.build_dataframe()
        assert df.iloc[0]["fuzz"] == True

    # Req: fuzz is NaN when parse fails
    def test_fuzz_nan_on_parse_failure(self, tmp_path):
        _write_trajectory(tmp_path, "run-1", 0, [
            {"position_index": 0, "question_id": "q1", "u": "p", "y": "gibberish", "parse_success": False, "score": None},
        ])
        evaluator = EvaluationLayer(str(tmp_path), [_StubCM("q1")])
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
        evaluator = EvaluationLayer(str(tmp_path), [_StubCM("q1"), _StubPR("q2")])
        df = evaluator.build_dataframe()
        assert len(df) == 4
        assert set(df["run_id"]) == {"run-1", "run-2"}


# --- Summary tests ---

class TestSummaries:
    @pytest.fixture
    def typed_eval(self, tmp_path):
        """Two runs, three question types, one parse failure."""
        _write_trajectory(tmp_path, "run-1", 0, [
            {"position_index": 0, "question_id": "q-cm", "u": "p", "y": "yes", "parse_success": True, "score": 1.0},
            {"position_index": 1, "question_id": "q-pr", "u": "p", "y": "no", "parse_success": True, "score": 0.0},
            {"position_index": 2, "question_id": "q-dj", "u": "p", "y": "yes", "parse_success": True, "score": 1.0},
        ])
        _write_trajectory(tmp_path, "run-2", 1, [
            {"position_index": 0, "question_id": "q-cm", "u": "p", "y": "yes", "parse_success": True, "score": 1.0},
            {"position_index": 1, "question_id": "q-pr", "u": "p", "y": "gibberish", "parse_success": False, "score": None},
            {"position_index": 2, "question_id": "q-dj", "u": "p", "y": "no", "parse_success": True, "score": 0.0},
        ])
        evaluator = EvaluationLayer(str(tmp_path), [_StubCM("q-cm"), _StubPR("q-pr"), _StubDJ("q-dj")])
        return evaluator, evaluator.build_dataframe()

    # Req: summary_by_question includes question_type, consistency_rate, parse_failure_rate, fuzz_rate, n_runs
    def test_summary_by_question_columns(self, typed_eval):
        evaluator, df = typed_eval
        summary = evaluator.summary_by_question(df)
        assert "question_type" in summary.columns
        assert "consistency_rate" in summary.columns
        assert "parse_failure_rate" in summary.columns
        assert "fuzz_rate" in summary.columns
        assert "n_runs" in summary.columns

    def test_summary_by_question_values(self, typed_eval):
        evaluator, df = typed_eval
        summary = evaluator.summary_by_question(df)
        # q-cm: 1.0 in both runs → consistency_rate 1.0
        assert summary.loc["q-cm", "consistency_rate"] == 1.0
        assert summary.loc["q-cm", "question_type"] == "CM"
        assert summary.loc["q-cm", "parse_failure_rate"] == 0.0
        assert summary.loc["q-cm", "n_runs"] == 2

    # Req: NaN scores excluded from mean (parse failures don't contaminate)
    def test_nan_excluded_from_consistency_rate(self, typed_eval):
        evaluator, df = typed_eval
        summary = evaluator.summary_by_question(df)
        # q-pr: run-1 score=0.0, run-2 parse_failure=NaN → mean should be 0.0
        assert summary.loc["q-pr", "consistency_rate"] == 0.0

    # Req: summary_by_question_type groups by CM/PR/DJ
    def test_summary_by_question_type_groups(self, typed_eval):
        evaluator, df = typed_eval
        summary = evaluator.summary_by_question_type(df)
        assert set(summary.index) == {"CM", "PR", "DJ"}
        assert "consistency_rate" in summary.columns

    def test_summary_by_question_type_values(self, typed_eval):
        evaluator, df = typed_eval
        summary = evaluator.summary_by_question_type(df)
        # CM: both runs yes → 1.0
        assert summary.loc["CM", "consistency_rate"] == 1.0
        # DJ: run-1 yes (1.0), run-2 no (0.0) → 0.5
        assert summary.loc["DJ", "consistency_rate"] == 0.5

    # Req: summary_by_position has consistency_rate, parse_failure_rate, n
    def test_summary_by_position_columns(self, typed_eval):
        evaluator, df = typed_eval
        summary = evaluator.summary_by_position(df)
        assert "consistency_rate" in summary.columns
        assert "parse_failure_rate" in summary.columns
        assert "n" in summary.columns
        assert 0 in summary.index.values

    # Req: summary_by_run has consistency_rate, parse_failure_rate, n_parsed
    def test_summary_by_run_columns(self, typed_eval):
        evaluator, df = typed_eval
        summary = evaluator.summary_by_run(df)
        assert "consistency_rate" in summary.columns
        assert "parse_failure_rate" in summary.columns
        assert "n_parsed" in summary.columns
        assert "run-1" in summary.index.values

    # Req: experiment_summary returns dict with expected keys
    def test_experiment_summary_keys(self, typed_eval):
        evaluator, df = typed_eval
        summary = evaluator.experiment_summary(df)
        assert isinstance(summary, dict)
        for key in ["total_turns", "parse_rate", "consistency_rate", "n_runs", "n_questions",
                     "CM_consistency_rate", "PR_consistency_rate", "DJ_consistency_rate",
                     "CM_parse_failure_rate", "PR_parse_failure_rate", "DJ_parse_failure_rate"]:
            assert key in summary, f"Missing key: {key}"

    def test_experiment_summary_values(self, typed_eval):
        evaluator, df = typed_eval
        summary = evaluator.experiment_summary(df)
        assert summary["total_turns"] == 6
        assert summary["n_runs"] == 2
        assert summary["n_questions"] == 3
        # 5 parsed out of 6
        assert abs(summary["parse_rate"] - 5 / 6) < 0.01
        # CM: 1.0, PR: 0.0, DJ: 0.5 → overall (1+1+0+1+0)/5 = 3/5 = 0.6
        assert abs(summary["consistency_rate"] - 0.6) < 0.01
        assert summary["CM_consistency_rate"] == 1.0
