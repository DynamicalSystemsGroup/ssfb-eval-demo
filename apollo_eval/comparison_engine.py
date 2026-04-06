"""Comparison engine for operator A vs B evaluation.

Runs both operators on the same probe sequence, scores responses against
ground-truth ontology, computes divergence, and optionally updates B's
belief graph to imitate A (online learning).
"""

import json
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from apollo_eval.divergence import DivergenceTrajectory, ProbeResult
from apollo_eval.evaluation import question_type
from apollo_eval.model_client import ModelClient
from apollo_eval.ontology_client import OntologyClient
from apollo_eval.question import Question


class ComparisonEngine:
    """Runs A vs B comparison across multiple epochs.

    Each epoch re-probes all questions in a shuffled order.
    A's history is reset per epoch (fresh pass).
    B's belief graph persists across epochs (accumulates learning).
    """

    def __init__(
        self,
        questions: list[Question],
        client_a: ModelClient,
        client_b: OntologyClient,
        n_epochs: int,
        seed: int,
        scenario_iri: str,
        imitation: bool = False,
        on_probe: Callable[[ProbeResult], None] | None = None,
        metadata: dict | None = None,
    ):
        self.questions = list(questions)
        self.client_a = client_a
        self.client_b = client_b
        self.n_epochs = n_epochs
        self.seed = seed
        self.scenario_iri = scenario_iri
        self.imitation = imitation
        self.on_probe = on_probe
        self.metadata = metadata or {}
        self._rng = random.Random(seed)
        self.run_id = str(uuid.uuid4())
        self.trajectory = DivergenceTrajectory(metadata={
            "run_id": self.run_id,
            "seed": seed,
            "scenario_iri": scenario_iri,
            "n_epochs": n_epochs,
            "imitation": imitation,
            **self.metadata,
        })

    def run_epoch(self, epoch: int) -> list[ProbeResult]:
        """Run one epoch: probe all questions with both operators.

        A's history is empty (reset per epoch).
        B's belief graph carries forward from prior epochs.
        """
        epoch_questions = list(self.questions)
        self._rng.shuffle(epoch_questions)

        a_history: list[tuple[str, str]] = []
        results = []

        for i, question in enumerate(epoch_questions):
            # Query both operators
            a_response = self.client_a.complete(a_history, question.prompt)
            b_response = self.client_b.complete([], question.prompt)

            # Score both against ground-truth ontology
            a_score = question.score(a_response)
            b_score = question.score(b_response)

            # Determine divergence: do A and B agree?
            if a_score.parse_success and b_score.parse_success:
                divergent = a_score.score != b_score.score
            else:
                divergent = False  # can't determine divergence if parse failed

            # Belief update (imitation mode)
            belief_update = None
            if self.imitation and a_score.parse_success:
                a_is_negated = question._detect_negation(a_response)
                belief_update = self.client_b.update_belief(question, a_is_negated)

            probe = ProbeResult(
                question_id=question.question_id,
                question_type=question_type(question),
                epoch=epoch,
                probe_index=i,
                a_response=a_response,
                b_response=b_response,
                a_score=a_score,
                b_score=b_score,
                divergent=divergent,
                belief_update=belief_update,
            )

            results.append(probe)
            self.trajectory.probes.append(probe)

            # Update A's history within this epoch
            a_history.append((question.prompt, a_response))

            if self.on_probe is not None:
                self.on_probe(probe)

        return results

    def run(self) -> DivergenceTrajectory:
        """Run all epochs and return the complete trajectory."""
        for epoch in range(self.n_epochs):
            self.run_epoch(epoch)
        return self.trajectory

    def save(self, output_dir: str) -> str:
        """Write trajectory JSON to the given directory."""
        path = Path(output_dir) / f"compare_{self.run_id}.json"

        data = {
            **self.trajectory.metadata,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "probes": [
                {
                    "question_id": p.question_id,
                    "question_type": p.question_type,
                    "epoch": p.epoch,
                    "probe_index": p.probe_index,
                    "a_response": p.a_response,
                    "b_response": p.b_response,
                    "a_parse_success": p.a_score.parse_success,
                    "b_parse_success": p.b_score.parse_success,
                    "a_score": p.a_score.score if p.a_score.parse_success else None,
                    "b_score": p.b_score.score if p.b_score.parse_success else None,
                    "divergent": p.divergent,
                    "belief_update": p.belief_update,
                }
                for p in self.trajectory.probes
            ],
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
        return str(path)
