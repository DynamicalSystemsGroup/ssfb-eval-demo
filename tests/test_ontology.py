import rdflib
import spacy
from spacy.matcher import PhraseMatcher

from apollo_eval.ontology import Ontology, ScoreResult


def _make_ontology():
    """Create a minimal Ontology for testing with empty/blank components."""
    graph = rdflib.Graph()
    nlp = spacy.blank("en")
    matcher = PhraseMatcher(nlp.vocab)
    return Ontology(graph=graph, nlp=nlp, matcher=matcher, vocab_labels=[])


class TestOntology:
    # Req: Ontology is a pure data container with graph, nlp, matcher fields
    def test_construction_with_valid_fields(self):
        ont = _make_ontology()
        assert isinstance(ont.graph, rdflib.Graph)
        assert isinstance(ont.nlp, spacy.Language)
        assert isinstance(ont.matcher, PhraseMatcher)

    # Req: graph, nlp, and matcher must always be consistent — constructed together
    def test_fields_are_accessible(self):
        ont = _make_ontology()
        assert ont.graph is not None
        assert ont.nlp is not None
        assert ont.matcher is not None

    # Req: Ontology is a dataclass — supports equality based on field values
    def test_is_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(Ontology)


class TestScoreResult:
    # Req: ScoreResult has question_id, parse_success, score fields
    def test_construction(self):
        result = ScoreResult(question_id="q-001", parse_success=True, score=1.0)
        assert result.question_id == "q-001"
        assert result.parse_success is True
        assert result.score == 1.0

    # Req: score is 1.0 (consistent) or 0.0 (contradicts ontology) when parse_success is True
    def test_consistent_score(self):
        result = ScoreResult(question_id="q-001", parse_success=True, score=1.0)
        assert result.score == 1.0

    def test_contradictory_score(self):
        result = ScoreResult(question_id="q-001", parse_success=True, score=0.0)
        assert result.score == 0.0

    # Req: parse failures are recorded separately — score not meaningful when parse_success is False
    def test_parse_failure(self):
        result = ScoreResult(question_id="q-001", parse_success=False, score=0.0)
        assert result.parse_success is False

    # Req: ScoreResult is a dataclass
    def test_is_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(ScoreResult)
