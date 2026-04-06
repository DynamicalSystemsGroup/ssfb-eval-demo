"""Divergence measurement data structures for operator comparison.

ProbeResult captures the outcome of probing both operators at a single point.
DivergenceTrajectory aggregates probe results across epochs and provides
DataFrame-based summaries for analysis.
"""

from dataclasses import dataclass, field

import pandas as pd

from apollo_eval.ontology import ScoreResult


@dataclass
class ProbeResult:
    """Result of probing both operators A and B at a single point x."""

    question_id: str
    question_type: str  # CM, PR, DJ
    epoch: int
    probe_index: int
    a_response: str
    b_response: str
    a_score: ScoreResult
    b_score: ScoreResult
    divergent: bool  # A and B disagree (when both parseable)
    belief_update: dict | None = None  # what B changed, or None


@dataclass
class DivergenceTrajectory:
    """Full trajectory of operator comparison across epochs."""

    probes: list[ProbeResult] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dataframe(self) -> pd.DataFrame:
        """Build a flat DataFrame from all probe results."""
        rows = []
        for p in self.probes:
            rows.append({
                "question_id": p.question_id,
                "question_type": p.question_type,
                "epoch": p.epoch,
                "probe_index": p.probe_index,
                "a_parse_success": p.a_score.parse_success,
                "b_parse_success": p.b_score.parse_success,
                "a_score": p.a_score.score if p.a_score.parse_success else float("nan"),
                "b_score": p.b_score.score if p.b_score.parse_success else float("nan"),
                "divergent": p.divergent,
                "belief_updated": p.belief_update is not None,
            })
        return pd.DataFrame(rows)

    def divergence_by_epoch(self) -> pd.DataFrame:
        """Per-epoch divergence rate — the convergence curve."""
        df = self.to_dataframe()
        if df.empty:
            return pd.DataFrame()
        return df.groupby("epoch").agg(
            divergence_rate=("divergent", "mean"),
            a_consistency=("a_score", "mean"),
            b_consistency=("b_score", "mean"),
            a_parse_rate=("a_parse_success", "mean"),
            b_parse_rate=("b_parse_success", "mean"),
            n_updates=("belief_updated", "sum"),
            n_probes=("question_id", "count"),
        )

    def divergence_by_type(self) -> pd.DataFrame:
        """Per-question-type divergence rate."""
        df = self.to_dataframe()
        if df.empty:
            return pd.DataFrame()
        return df.groupby("question_type").agg(
            divergence_rate=("divergent", "mean"),
            a_consistency=("a_score", "mean"),
            b_consistency=("b_score", "mean"),
            n_probes=("question_id", "count"),
        )

    def divergence_by_question(self) -> pd.DataFrame:
        """Per-question divergence across all epochs."""
        df = self.to_dataframe()
        if df.empty:
            return pd.DataFrame()
        return df.groupby(["question_id", "question_type"]).agg(
            divergence_rate=("divergent", "mean"),
            a_consistency=("a_score", "mean"),
            b_consistency=("b_score", "mean"),
            n_epochs=("epoch", "nunique"),
        )

    def summary(self) -> dict:
        """Overall summary statistics."""
        df = self.to_dataframe()
        if df.empty:
            return {"total_probes": 0}
        return {
            "total_probes": len(df),
            "n_epochs": df["epoch"].nunique(),
            "n_questions": df["question_id"].nunique(),
            "overall_divergence_rate": df["divergent"].mean(),
            "a_consistency_rate": df["a_score"].mean(),
            "b_consistency_rate": df["b_score"].mean(),
            "a_parse_rate": df["a_parse_success"].mean(),
            "b_parse_rate": df["b_parse_success"].mean(),
            "total_belief_updates": int(df["belief_updated"].sum()),
        }
