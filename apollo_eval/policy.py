"""Semantic state feedback policy engine.

Implements π_ω(m_t) → u_{t+1}: samples questions from a memory pool without
replacement, sends prompts to an LLM, scores responses, and records trajectories.

Memory m_t is the pool of unasked questions (shrinks).
History h_t is the full realization of (u, y) pairs (grows monotonically).
"""

import json
import random
import uuid
from pathlib import Path
from typing import Callable

from apollo_eval.model_client import ModelClient


def default_exit_criteria(memory: list) -> bool:
    """Exit when the question pool is exhausted."""
    return len(memory) == 0


class PolicyEngine:
    """Runs one trajectory: samples questions, queries the LLM, scores, logs.

    Each PolicyEngine instance represents one independent run with its own
    seed, memory pool, history, and run_id. Instantiate fresh per run.
    """

    def __init__(
        self,
        questions: list,
        client: ModelClient,
        seed: int,
        scenario_iri: str,
        exit_criteria: Callable[[list], bool] = default_exit_criteria,
    ):
        self.questions = list(questions)  # defensive copy — this IS the memory pool
        self.client = client
        self.seed = seed
        self.scenario_iri = scenario_iri
        self.exit_criteria = exit_criteria
        self._rng = random.Random(seed)
        self.run_id = str(uuid.uuid4())
        self.history: list[tuple[str, str]] = []
        self.trajectory: list[dict] = []

    def step(self) -> dict:
        """Execute one turn of the policy loop.

        Samples a question from memory, queries the client with full history,
        scores the response, and records the turn. Returns the turn record.
        """
        # π_ω(m_t): sample one question from the pool
        idx = self._rng.randrange(len(self.questions))
        question = self.questions.pop(idx)  # M(u, y, m) = m \ {q}

        # Query the LLM
        response = self.client.complete(self.history, question.prompt)

        # Score
        result = question.score(response)

        # Build turn record
        turn = {
            "position_index": len(self.trajectory),
            "question_id": question.question_id,
            "u": question.prompt,
            "y": response,
            "parse_success": result.parse_success,
            "score": result.score if result.parse_success else None,
        }

        # Update state
        self.history.append((question.prompt, response))
        self.trajectory.append(turn)
        return turn

    def run(self) -> dict:
        """Run the full trajectory until exit criteria are met.

        Returns the complete trajectory dict ready for JSON serialization.
        """
        while not self.exit_criteria(self.questions):
            self.step()
        return {
            "run_id": self.run_id,
            "seed": self.seed,
            "scenario_iri": self.scenario_iri,
            "turns": self.trajectory,
        }

    def save(self, trajectory_dir: str) -> str:
        """Write trajectory JSON to the given directory.

        Returns the path to the written file.
        """
        path = Path(trajectory_dir) / f"{self.run_id}.json"
        trajectory_data = {
            "run_id": self.run_id,
            "seed": self.seed,
            "scenario_iri": self.scenario_iri,
            "turns": self.trajectory,
        }
        path.write_text(json.dumps(trajectory_data, indent=2))
        return str(path)
