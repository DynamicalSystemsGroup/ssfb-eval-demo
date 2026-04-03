"""Post-hoc evaluation layer — loads trajectories, re-scores, builds DataFrame.

Runs after all trajectory runs are collected. Re-scores each turn using the
Question instances (authoritative) rather than trusting stored JSON scores.
Produces a pandas DataFrame supporting analysis by question, run, and position.
"""

import json
from pathlib import Path

import pandas as pd

from apollo_eval.question import (
    ClassMembershipQuestion,
    PropertyRestrictionQuestion,
    DisjointnessQuestion,
)
from apollo_eval.question_loader import get_question_map


def question_type(question) -> str:
    """Return short type code for a question instance: CM, PR, or DJ."""
    if isinstance(question, ClassMembershipQuestion):
        return "CM"
    elif isinstance(question, PropertyRestrictionQuestion):
        return "PR"
    elif isinstance(question, DisjointnessQuestion):
        return "DJ"
    return "UNKNOWN"


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

        Columns: question_id, question_type, run_id, position_index,
                 parse_success, score, fuzz
        """
        rows = []
        for trajectory in self.load_trajectories():
            run_id = trajectory["run_id"]
            seed = trajectory.get("seed")
            for turn in trajectory["turns"]:
                question = self.question_map[turn["question_id"]]
                result = question.score(turn["y"])
                rows.append({
                    "question_id": turn["question_id"],
                    "question_type": question_type(question),
                    "run_id": run_id,
                    "seed": seed,
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
        """Per-question stats: type, consistency rate, parse/fuzz rates, count."""
        return df.groupby("question_id").agg(
            question_type=("question_type", "first"),
            consistency_rate=("score", "mean"),
            parse_failure_rate=("parse_success", lambda x: (~x).mean()),
            fuzz_rate=("fuzz", lambda x: x.dropna().mean() if x.notna().any() else float("nan")),
            n_runs=("run_id", "count"),
        )

    def summary_by_question_type(self, df: pd.DataFrame) -> pd.DataFrame:
        """Per-type stats (CM, PR, DJ)."""
        return df.groupby("question_type").agg(
            consistency_rate=("score", "mean"),
            parse_failure_rate=("parse_success", lambda x: (~x).mean()),
            fuzz_rate=("fuzz", lambda x: x.dropna().mean() if x.notna().any() else float("nan")),
            n=("question_id", "count"),
        )

    def summary_by_position(self, df: pd.DataFrame) -> pd.DataFrame:
        """Per-position stats for position-effect analysis."""
        return df.groupby("position_index").agg(
            consistency_rate=("score", "mean"),
            parse_failure_rate=("parse_success", lambda x: (~x).mean()),
            n=("question_id", "count"),
        )

    def summary_by_run(self, df: pd.DataFrame) -> pd.DataFrame:
        """Per-run stats showing variance across seeds."""
        return df.groupby("run_id").agg(
            consistency_rate=("score", "mean"),
            parse_failure_rate=("parse_success", lambda x: (~x).mean()),
            n_parsed=("parse_success", "sum"),
        )

    def experiment_summary(self, df: pd.DataFrame) -> dict:
        """Overall experiment statistics as a flat dictionary."""
        n_total = len(df)
        n_parsed = int(df["parse_success"].sum())
        parsed_df = df[df["parse_success"]]

        result = {
            "total_turns": n_total,
            "parse_rate": n_parsed / n_total if n_total > 0 else 0.0,
            "consistency_rate": parsed_df["score"].mean() if not parsed_df.empty else 0.0,
            "n_runs": df["run_id"].nunique(),
            "n_questions": df["question_id"].nunique(),
        }

        for qt in ("CM", "PR", "DJ"):
            subset = df[df["question_type"] == qt]
            parsed_subset = subset[subset["parse_success"]]
            result[f"{qt}_consistency_rate"] = (
                parsed_subset["score"].mean() if not parsed_subset.empty else float("nan")
            )
            result[f"{qt}_parse_failure_rate"] = (
                (~subset["parse_success"]).mean() if not subset.empty else 0.0
            )

        return result
