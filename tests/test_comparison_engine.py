"""Tests for comparison_engine.py — ComparisonEngine.

Uses stub clients and questions. No Ollama or real ontology needed.
"""

import json

import rdflib
from rdflib import Namespace
from rdflib.namespace import RDF

import pytest

from apollo_eval.model_client import ModelClient
from apollo_eval.ontology import Ontology, ScoreResult
from apollo_eval.ontology_client import OntologyClient
from apollo_eval.comparison_engine import ComparisonEngine
from apollo_eval.question import ClassMembershipQuestion, Question


SCENARIO = Namespace("http://example.org/test/")


def _make_stub_ontology(triples=None):
    """Build a minimal Ontology for testing."""
    import spacy
    from spacy.matcher import PhraseMatcher

    graph = rdflib.Graph()
    if triples:
        for t in triples:
            graph.add(t)

    nlp = spacy.blank("en")
    matcher = PhraseMatcher(nlp.vocab)
    return Ontology(
        graph=graph, nlp=nlp, matcher=matcher,
        vocab_labels=[], similarity_threshold=1.0,
    )


class _StubClientA(ModelClient):
    """Model A stub that returns configurable responses per prompt."""

    def __init__(self, responses: dict[str, str] | None = None, default: str = "Yes, dog is an animal."):
        self.responses = responses or {}
        self.default = default
        self.calls: list[tuple[list, str]] = []

    def complete(self, history, prompt):
        self.calls.append((list(history), prompt))
        return self.responses.get(prompt, self.default)


class _StubQuestion:
    """Minimal question stub for ComparisonEngine tests."""

    def __init__(self, question_id: str, prompt: str, score_val: float = 1.0, parse: bool = True):
        self.question_id = question_id
        self.prompt = prompt
        self._score_val = score_val
        self._parse = parse

    def score(self, response: str) -> ScoreResult:
        return ScoreResult(
            question_id=self.question_id,
            parse_success=self._parse,
            score=self._score_val if self._parse else 0.0,
            fuzz=False if self._parse else None,
        )

    def _detect_negation(self, response: str) -> bool:
        return "not" in response.lower() or "no" in response.lower()


class _StubOntologyClient(OntologyClient):
    """OntologyClient stub that returns fixed responses without needing real ontology."""

    def __init__(self, responses: dict[str, str] | None = None, default: str = "Yes, dog is an animal."):
        self.responses = responses or {}
        self.default = default
        self.prompt_to_question = {}
        self.belief_graph = rdflib.Graph()
        self._updates: list[dict] = []

    def complete(self, history, prompt):
        return self.responses.get(prompt, self.default)

    def update_belief(self, question, a_is_negated):
        record = {"question_id": question.question_id, "a_is_negated": a_is_negated}
        self._updates.append(record)
        return record


# --- Tests ---

class TestComparisonEngineBasic:
    # Req: runs both operators on same questions
    def test_runs_both_operators(self):
        questions = [_StubQuestion("q1", "prompt 1"), _StubQuestion("q2", "prompt 2")]
        client_a = _StubClientA()
        client_b = _StubOntologyClient()

        engine = ComparisonEngine(
            questions=questions, client_a=client_a, client_b=client_b,
            n_epochs=1, seed=42, scenario_iri="test",
        )
        trajectory = engine.run()

        assert len(trajectory.probes) == 2
        assert len(client_a.calls) == 2

    # Req: each probe records both A and B responses
    def test_records_both_responses(self):
        questions = [_StubQuestion("q1", "prompt 1")]
        client_a = _StubClientA(default="A says yes")
        client_b = _StubOntologyClient(default="B says yes")

        engine = ComparisonEngine(
            questions=questions, client_a=client_a, client_b=client_b,
            n_epochs=1, seed=0, scenario_iri="test",
        )
        trajectory = engine.run()

        probe = trajectory.probes[0]
        assert probe.a_response == "A says yes"
        assert probe.b_response == "B says yes"


class TestComparisonEngineEpochs:
    # Req: multi-epoch runs re-probe all questions each epoch
    def test_multi_epoch_reprobes(self):
        questions = [_StubQuestion("q1", "p1"), _StubQuestion("q2", "p2")]
        client_a = _StubClientA()
        client_b = _StubOntologyClient()

        engine = ComparisonEngine(
            questions=questions, client_a=client_a, client_b=client_b,
            n_epochs=3, seed=0, scenario_iri="test",
        )
        trajectory = engine.run()

        assert len(trajectory.probes) == 6  # 2 questions * 3 epochs
        epochs = {p.epoch for p in trajectory.probes}
        assert epochs == {0, 1, 2}

    # Req: A's history resets each epoch
    def test_a_history_resets_per_epoch(self):
        questions = [_StubQuestion("q1", "p1")]
        client_a = _StubClientA()
        client_b = _StubOntologyClient()

        engine = ComparisonEngine(
            questions=questions, client_a=client_a, client_b=client_b,
            n_epochs=2, seed=0, scenario_iri="test",
        )
        engine.run()

        # Both epochs should start with empty history
        # Epoch 0, probe 0: history should be empty
        assert client_a.calls[0][0] == []
        # Epoch 1, probe 0: history should also be empty (reset)
        assert client_a.calls[1][0] == []


class _ResponseDependentQuestion:
    """Question stub that scores based on response content."""

    def __init__(self, question_id: str, prompt: str):
        self.question_id = question_id
        self.prompt = prompt

    def score(self, response: str) -> ScoreResult:
        # A's response contains "A says", B's contains "B says"
        # Score A=0.0, B=1.0 to create divergence
        val = 0.0 if "A says" in response else 1.0
        return ScoreResult(
            question_id=self.question_id,
            parse_success=True, score=val, fuzz=False,
        )

    def _detect_negation(self, response: str) -> bool:
        return "not" in response.lower()


class TestComparisonEngineDivergence:
    # Req: divergent=True when A and B scores differ
    def test_detects_divergence(self):
        q = _ResponseDependentQuestion("q1", "p1")
        client_a = _StubClientA(default="A says yes")
        client_b = _StubOntologyClient(default="B says yes")

        engine = ComparisonEngine(
            questions=[q], client_a=client_a, client_b=client_b,
            n_epochs=1, seed=0, scenario_iri="test",
        )
        trajectory = engine.run()

        assert len(trajectory.probes) == 1
        assert trajectory.probes[0].divergent is True

    # Req: parse failure means divergent=False (can't determine)
    def test_parse_failure_not_divergent(self):
        q = _StubQuestion("q1", "p1", parse=False)
        client_a = _StubClientA()
        client_b = _StubOntologyClient()

        engine = ComparisonEngine(
            questions=[q], client_a=client_a, client_b=client_b,
            n_epochs=1, seed=0, scenario_iri="test",
        )
        trajectory = engine.run()
        assert trajectory.probes[0].divergent is False


class TestComparisonEngineImitation:
    # Req: imitation mode calls update_belief on B
    def test_imitation_updates_belief(self):
        questions = [_StubQuestion("q1", "p1")]
        client_a = _StubClientA()
        client_b = _StubOntologyClient()

        engine = ComparisonEngine(
            questions=questions, client_a=client_a, client_b=client_b,
            n_epochs=1, seed=0, scenario_iri="test",
            imitation=True,
        )
        engine.run()

        assert len(client_b._updates) == 1

    # Req: imitation=False does not call update_belief
    def test_no_imitation_no_updates(self):
        questions = [_StubQuestion("q1", "p1")]
        client_a = _StubClientA()
        client_b = _StubOntologyClient()

        engine = ComparisonEngine(
            questions=questions, client_a=client_a, client_b=client_b,
            n_epochs=1, seed=0, scenario_iri="test",
            imitation=False,
        )
        engine.run()

        assert len(client_b._updates) == 0


class TestComparisonEngineCallbacks:
    # Req: on_probe callback fires for each probe
    def test_on_probe_callback(self):
        fired = []
        questions = [_StubQuestion("q1", "p1"), _StubQuestion("q2", "p2")]
        client_a = _StubClientA()
        client_b = _StubOntologyClient()

        engine = ComparisonEngine(
            questions=questions, client_a=client_a, client_b=client_b,
            n_epochs=1, seed=0, scenario_iri="test",
            on_probe=lambda p: fired.append(p),
        )
        engine.run()

        assert len(fired) == 2


class TestComparisonEngineSave:
    # Req: save() writes valid JSON with expected structure
    def test_save_trajectory(self, tmp_path):
        questions = [_StubQuestion("q1", "p1")]
        client_a = _StubClientA()
        client_b = _StubOntologyClient()

        engine = ComparisonEngine(
            questions=questions, client_a=client_a, client_b=client_b,
            n_epochs=1, seed=0, scenario_iri="test",
        )
        engine.run()
        path = engine.save(str(tmp_path))

        data = json.loads(open(path).read())
        assert "probes" in data
        assert len(data["probes"]) == 1
        assert data["probes"][0]["question_id"] == "q1"
        assert "a_response" in data["probes"][0]
        assert "b_response" in data["probes"][0]
        assert "divergent" in data["probes"][0]


class TestDivergenceTrajectoryDataFrame:
    # Req: trajectory produces valid DataFrame with expected columns
    def test_to_dataframe(self):
        questions = [_StubQuestion("q1", "p1"), _StubQuestion("q2", "p2")]
        client_a = _StubClientA()
        client_b = _StubOntologyClient()

        engine = ComparisonEngine(
            questions=questions, client_a=client_a, client_b=client_b,
            n_epochs=2, seed=0, scenario_iri="test",
        )
        trajectory = engine.run()
        df = trajectory.to_dataframe()

        assert len(df) == 4  # 2 questions * 2 epochs
        expected_cols = {"question_id", "question_type", "epoch", "probe_index",
                         "a_parse_success", "b_parse_success", "a_score", "b_score",
                         "divergent", "belief_updated"}
        assert expected_cols.issubset(set(df.columns))

    # Req: divergence_by_epoch produces per-epoch summary
    def test_divergence_by_epoch(self):
        questions = [_StubQuestion("q1", "p1")]
        client_a = _StubClientA()
        client_b = _StubOntologyClient()

        engine = ComparisonEngine(
            questions=questions, client_a=client_a, client_b=client_b,
            n_epochs=3, seed=0, scenario_iri="test",
        )
        trajectory = engine.run()
        by_epoch = trajectory.divergence_by_epoch()

        assert len(by_epoch) == 3
        assert "divergence_rate" in by_epoch.columns

    # Req: summary returns overall statistics
    def test_summary(self):
        questions = [_StubQuestion("q1", "p1")]
        client_a = _StubClientA()
        client_b = _StubOntologyClient()

        engine = ComparisonEngine(
            questions=questions, client_a=client_a, client_b=client_b,
            n_epochs=2, seed=0, scenario_iri="test",
        )
        trajectory = engine.run()
        s = trajectory.summary()

        assert s["total_probes"] == 2
        assert s["n_epochs"] == 2
        assert s["n_questions"] == 1
        assert "overall_divergence_rate" in s
