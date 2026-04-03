import rdflib
from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL

import pytest

from apollo_eval.ontology import Ontology, ScoreResult
from apollo_eval.vocab import OntologyVocabularyBuilder
from apollo_eval.question import Question

EX = Namespace("http://example.org/")


def _build_test_ontology():
    """Build a small Ontology with known labels for extraction testing."""
    g = rdflib.Graph()
    g.bind("ex", EX)
    g.add((EX.Measles, RDF.type, OWL.Class))
    g.add((EX.Measles, RDFS.label, Literal("measles")))
    g.add((EX.InfectiousDisease, RDF.type, OWL.Class))
    g.add((EX.InfectiousDisease, RDFS.label, Literal("infectious disease")))
    g.add((EX.Vaccination, RDF.type, OWL.Class))
    g.add((EX.Vaccination, RDFS.label, Literal("vaccination")))
    g.add((EX.Airborne, RDF.type, OWL.NamedIndividual))
    g.add((EX.Airborne, RDFS.label, Literal("airborne")))
    return OntologyVocabularyBuilder(g).build()


class _StubQuestion(Question):
    """Minimal concrete subclass for testing the base class."""

    def __init__(self, question_id: str, prompt: str):
        self.question_id = question_id
        self.prompt = prompt

    def _check(self, extracted_terms: list[str]) -> bool:
        # Always returns True for stub purposes
        return True


@pytest.fixture(autouse=True)
def _set_ontology():
    """Set the class-level ontology before each test, clean up after."""
    ont = _build_test_ontology()
    Question.ontology = ont
    yield
    Question.ontology = None


class TestQuestionBaseClass:
    # Req: Question.ontology is a class-level attribute set once
    def test_class_level_ontology(self):
        assert isinstance(Question.ontology, Ontology)

    # Req: Question base class has question_id and prompt attributes
    def test_stub_has_required_attributes(self):
        q = _StubQuestion("q-001", "What is measles?")
        assert q.question_id == "q-001"
        assert q.prompt == "What is measles?"

    # Req: score() always returns a ScoreResult
    def test_score_returns_score_result(self):
        q = _StubQuestion("q-001", "What is measles?")
        result = q.score("Measles is an infectious disease.")
        assert isinstance(result, ScoreResult)

    # Req: score() returns correct question_id
    def test_score_result_has_correct_question_id(self):
        q = _StubQuestion("q-002", "prompt")
        result = q.score("Measles is an infectious disease.")
        assert result.question_id == "q-002"

    # Req: Cannot instantiate Question directly (abstract)
    def test_cannot_instantiate_base_class(self):
        with pytest.raises(TypeError):
            Question()


class TestExtraction:
    # Req: extraction maps response text to valid RDF terms from controlled vocabulary
    def test_extracts_single_word_term(self):
        q = _StubQuestion("q-001", "prompt")
        terms = q._extract_terms("The patient received vaccination.")
        assert "vaccination" in terms

    # Req: extraction recognizes multi-word ontology labels
    def test_extracts_multi_word_term(self):
        q = _StubQuestion("q-001", "prompt")
        terms = q._extract_terms("Measles is an infectious disease.")
        assert "infectious disease" in terms

    # Req: extraction finds multiple terms in a single response
    def test_extracts_multiple_terms(self):
        q = _StubQuestion("q-001", "prompt")
        terms = q._extract_terms("Measles is an infectious disease spread by airborne transmission.")
        assert "measles" in terms
        assert "infectious disease" in terms
        assert "airborne" in terms

    # Req: extraction returns empty list when no ontology terms found
    def test_returns_empty_for_no_matches(self):
        q = _StubQuestion("q-001", "prompt")
        terms = q._extract_terms("The weather is sunny today.")
        assert terms == []

    # Req: extraction is case-insensitive (grounding step, not exact match)
    def test_case_insensitive_extraction(self):
        q = _StubQuestion("q-001", "prompt")
        terms = q._extract_terms("MEASLES is a well-known condition.")
        assert "measles" in terms

    # Req: parse failures (no extraction) do not raise — score returns parse_success=False
    def test_parse_failure_returns_false(self):
        q = _StubQuestion("q-001", "prompt")
        result = q.score("The weather is sunny today.")
        assert result.parse_success is False

    # Req: parse failures never raise exceptions
    def test_no_exception_on_empty_response(self):
        q = _StubQuestion("q-001", "prompt")
        result = q.score("")
        assert isinstance(result, ScoreResult)
        assert result.parse_success is False
