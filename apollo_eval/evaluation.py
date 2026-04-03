"""Post-hoc evaluation layer — loads trajectories, re-scores, builds DataFrame.

Runs after all trajectory runs are collected. Re-scores each turn using the
Question instances (authoritative) rather than trusting stored JSON scores.
Produces a pandas DataFrame supporting analysis by question, run, and position.
"""

import json
import math
from pathlib import Path

import pandas as pd

from apollo_eval.question_loader import get_question_map


class EvaluationLayer:
    """Loads trajectory JSONs, re-scores responses, and builds analysis DataFrames."""

    def __init__(self, trajectory_dir: str, questions: list):
        self.trajectory_dir = Path(trajectory_dir)
        self.question_map = get_question_map(questions)

    def load_trajectories(self) -> list[dict]:
        """Load all trajectory JSON files from the directory, sorted by name."""
        trajectories = []
        for path in sorted(self.trajectory_dir.glob("*.json")):
            with open(path) as f:
                trajectories.append(json.load(f))
        return trajectories

    def build_dataframe(self) -> pd.DataFrame:
        """Build the evaluation DataFrame from all trajectories.

        Re-scores each turn via question.score(y) for authoritative results.
        Parse failures produce NaN in score and fuzz columns.

        Columns: question_id, run_id, position_index, parse_success, score, fuzz
        """
        rows = []
        for trajectory in self.load_trajectories():
            run_id = trajectory["run_id"]
            for turn in trajectory["turns"]:
                question = self.question_map[turn["question_id"]]
                result = question.score(turn["y"])
                rows.append({
                    "question_id": turn["question_id"],
                    "run_id": run_id,
                    "position_index": turn["position_index"],
                    "parse_success": result.parse_success,
                    "score": result.score if result.parse_success else float("nan"),
                    "fuzz": result.fuzz if result.parse_success else None,
                })

        df = pd.DataFrame(rows)
        if not df.empty:
            df["parse_success"] = df["parse_success"].astype(bool)
        return df

    def summary_by_question(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mean consistency rate and parse failure rate by question_id."""
        return df.groupby("question_id").agg(
            score=("score", "mean"),
            parse_failure_rate=("parse_success", lambda x: (~x).mean()),
        )

    def summary_by_position(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mean consistency rate by position_index."""
        return df.groupby("position_index").agg(
            score=("score", "mean"),
        )

    def summary_by_run(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mean consistency rate by run_id."""
        return df.groupby("run_id").agg(
            score=("score", "mean"),
        )
