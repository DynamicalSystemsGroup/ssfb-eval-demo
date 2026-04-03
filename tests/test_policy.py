"""Tests for policy.py — PolicyEngine and default_exit_criteria.

Uses stub ModelClient and stub Question instances — no Ollama or ontology needed.
"""

import json

import pytest

from apollo_eval.model_client import ModelClient
from apollo_eval.ontology import ScoreResult
from apollo_eval.policy import PolicyEngine, default_exit_criteria


# --- Stubs ---

class _StubClient(ModelClient):
    """Returns a canned response, records calls for assertion."""

    def __init__(self, response: str = "stub response"):
        self.response = response
        self.calls: list[tuple[list, str]] = []

    def complete(self, history, prompt):
        self.calls.append((list(history), prompt))
        return self.response


class _StubQuestion:
    """Minimal question that always parses and scores 1.0."""

    def __init__(self, question_id: str, prompt: str = "stub prompt"):
        self.question_id = question_id
        self.prompt = prompt

    def score(self, response: str) -> ScoreResult:
        return ScoreResult(
            question_id=self.question_id,
            parse_success=True,
            score=1.0,
            fuzz=False,
        )


class _NonParseQuestion:
    """Question that always fails to parse."""

    def __init__(self, question_id: str, prompt: str = "nonparse prompt"):
        self.question_id = question_id
        self.prompt = prompt

    def score(self, response: str) -> ScoreResult:
        return ScoreResult(
            question_id=self.question_id,
            parse_success=False,
            score=0.0,
            fuzz=None,
        )


# --- Tests ---

class TestDefaultExitCriteria:
    # Req: exit when memory pool is empty
    def test_empty_pool_returns_true(self):
        assert default_exit_criteria([]) is True

    # Req: do not exit when questions remain
    def test_nonempty_pool_returns_false(self):
        assert default_exit_criteria([_StubQuestion("q1")]) is False


class TestPolicyEngineStep:
    # Req: memory operator M removes the asked question from pool
    def test_step_removes_question_from_pool(self):
        questions = [_StubQuestion(f"q{i}") for i in range(3)]
        engine = PolicyEngine(questions, _StubClient(), seed=0, scenario_iri="test")
        assert len(engine.questions) == 3
        engine.step()
        assert len(engine.questions) == 2

    # Req: history grows monotonically with (u, y) pairs
    def test_step_appends_to_history(self):
        questions = [_StubQuestion("q1")]
        client = _StubClient("the response")
        engine = PolicyEngine(questions, client, seed=0, scenario_iri="test")
        engine.step()
        assert len(engine.history) == 1
        assert engine.history[0][1] == "the response"

    # Req: step returns turn record with correct schema
    def test_step_returns_turn_record(self):
        questions = [_StubQuestion("q1", prompt="What is X?")]
        engine = PolicyEngine(questions, _StubClient("Y"), seed=0, scenario_iri="test")
        turn = engine.step()
        assert turn["position_index"] == 0
        assert turn["question_id"] == "q1"
        assert turn["u"] == "What is X?"
        assert turn["y"] == "Y"
        assert turn["parse_success"] is True
        assert turn["score"] == 1.0

    # Req: position_index increments with each step
    def test_position_index_increments(self):
        questions = [_StubQuestion(f"q{i}") for i in range(3)]
        engine = PolicyEngine(questions, _StubClient(), seed=0, scenario_iri="test")
        for i in range(3):
            turn = engine.step()
            assert turn["position_index"] == i

    # Req: score is None when parse_success is False
    def test_parse_failure_score_null(self):
        questions = [_NonParseQuestion("q1")]
        engine = PolicyEngine(questions, _StubClient(), seed=0, scenario_iri="test")
        turn = engine.step()
        assert turn["parse_success"] is False
        assert turn["score"] is None

    # Req: history is passed to client for multi-turn context
    def test_history_passed_to_client(self):
        questions = [_StubQuestion(f"q{i}", prompt=f"prompt {i}") for i in range(3)]
        client = _StubClient("resp")
        engine = PolicyEngine(questions, client, seed=0, scenario_iri="test")
        engine.step()
        engine.step()
        engine.step()
        # First call: empty history
        assert client.calls[0][0] == []
        # Second call: one prior turn
        assert len(client.calls[1][0]) == 1
        # Third call: two prior turns
        assert len(client.calls[2][0]) == 2


class TestPolicyEngineRun:
    # Req: run exhausts the question pool
    def test_run_exhausts_pool(self):
        questions = [_StubQuestion(f"q{i}") for i in range(5)]
        engine = PolicyEngine(questions, _StubClient(), seed=0, scenario_iri="test")
        trajectory = engine.run()
        assert len(engine.questions) == 0
        assert len(trajectory["turns"]) == 5

    # Req: trajectory dict has correct top-level schema
    def test_run_returns_trajectory_schema(self):
        questions = [_StubQuestion("q1")]
        engine = PolicyEngine(questions, _StubClient(), seed=42, scenario_iri="http://example.org/test")
        trajectory = engine.run()
        assert "run_id" in trajectory
        assert trajectory["seed"] == 42
        assert trajectory["scenario_iri"] == "http://example.org/test"
        assert isinstance(trajectory["turns"], list)

    # Req: same seed produces same question order
    def test_deterministic_with_seed(self):
        def make_questions():
            return [_StubQuestion(f"q{i}") for i in range(10)]

        engine1 = PolicyEngine(make_questions(), _StubClient(), seed=7, scenario_iri="test")
        engine2 = PolicyEngine(make_questions(), _StubClient(), seed=7, scenario_iri="test")
        t1 = engine1.run()
        t2 = engine2.run()
        order1 = [t["question_id"] for t in t1["turns"]]
        order2 = [t["question_id"] for t in t2["turns"]]
        assert order1 == order2

    # Req: different seeds produce different question order
    def test_different_seeds_different_order(self):
        def make_questions():
            return [_StubQuestion(f"q{i}") for i in range(10)]

        engine1 = PolicyEngine(make_questions(), _StubClient(), seed=0, scenario_iri="test")
        engine2 = PolicyEngine(make_questions(), _StubClient(), seed=99, scenario_iri="test")
        t1 = engine1.run()
        t2 = engine2.run()
        order1 = [t["question_id"] for t in t1["turns"]]
        order2 = [t["question_id"] for t in t2["turns"]]
        assert order1 != order2

    # Req: defensive copy — caller's list is not mutated
    def test_does_not_mutate_input_list(self):
        questions = [_StubQuestion(f"q{i}") for i in range(3)]
        original_len = len(questions)
        engine = PolicyEngine(questions, _StubClient(), seed=0, scenario_iri="test")
        engine.run()
        assert len(questions) == original_len


class TestPolicyEngineSave:
    # Req: save writes valid JSON with correct schema
    def test_save_writes_json(self, tmp_path):
        questions = [_StubQuestion("q1")]
        engine = PolicyEngine(questions, _StubClient(), seed=0, scenario_iri="test")
        engine.run()
        path = engine.save(str(tmp_path))
        with open(path) as f:
            data = json.load(f)
        assert data["run_id"] == engine.run_id
        assert data["seed"] == 0
        assert len(data["turns"]) == 1

    # Req: file is named {run_id}.json
    def test_filename_is_run_id(self, tmp_path):
        questions = [_StubQuestion("q1")]
        engine = PolicyEngine(questions, _StubClient(), seed=0, scenario_iri="test")
        engine.run()
        path = engine.save(str(tmp_path))
        assert path.endswith(f"{engine.run_id}.json")


class TestPolicyEngineCustomExit:
    # Req: exit predicate is pluggable
    def test_custom_exit_criteria(self):
        questions = [_StubQuestion(f"q{i}") for i in range(10)]
        # Stop after 3 questions
        engine = PolicyEngine(
            questions, _StubClient(), seed=0, scenario_iri="test",
            exit_criteria=lambda mem: len(mem) <= 7,
        )
        trajectory = engine.run()
        assert len(trajectory["turns"]) == 3
