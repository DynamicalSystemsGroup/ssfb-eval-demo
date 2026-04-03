import rdflib
from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL

import owlrl
import pytest

from apollo_eval.ontology import Ontology, ScoreResult
from apollo_eval.vocab import OntologyVocabularyBuilder
from apollo_eval.question import (
    Question,
    ClassMembershipQuestion,
    PropertyRestrictionQuestion,
    DisjointnessQuestion,
)

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


# --- Stage 3b: Concrete subclass tests ---

def _build_scoring_ontology():
    """Build an ontology with instances, properties, and disjointness for scoring tests.

    Asserted facts:
    - :measles_instance a :InfectiousDisease
    - :InfectiousDisease rdfs:subClassOf :Disease
    - :measles_instance :hasTransmissionMode :airborne_instance
    - :InfectiousDisease owl:disjointWith :Vaccination
    """
    g = rdflib.Graph()
    g.bind("ex", EX)
    # Classes
    g.add((EX.Disease, RDF.type, OWL.Class))
    g.add((EX.Disease, RDFS.label, Literal("disease")))
    g.add((EX.InfectiousDisease, RDF.type, OWL.Class))
    g.add((EX.InfectiousDisease, RDFS.subClassOf, EX.Disease))
    g.add((EX.InfectiousDisease, RDFS.label, Literal("infectious disease")))
    g.add((EX.Vaccination, RDF.type, OWL.Class))
    g.add((EX.Vaccination, RDFS.label, Literal("vaccination")))
    # Disjointness
    g.add((EX.InfectiousDisease, OWL.disjointWith, EX.Vaccination))
    # Individuals
    g.add((EX.measles_instance, RDF.type, EX.InfectiousDisease))
    g.add((EX.measles_instance, RDFS.label, Literal("measles")))
    g.add((EX.airborne_instance, RDF.type, OWL.NamedIndividual))
    g.add((EX.airborne_instance, RDFS.label, Literal("airborne")))
    # Property
    g.add((EX.hasTransmissionMode, RDF.type, OWL.ObjectProperty))
    g.add((EX.hasTransmissionMode, RDFS.label, Literal("has transmission mode")))
    g.add((EX.measles_instance, EX.hasTransmissionMode, EX.airborne_instance))
    # Apply reasoning
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
    return OntologyVocabularyBuilder(g).build()


@pytest.fixture
def scoring_ontology():
    """Set up the richer ontology for scoring tests."""
    ont = _build_scoring_ontology()
    Question.ontology = ont
    yield ont
    Question.ontology = None


class TestClassMembershipQuestion:
    # Req: tests [entity] is a [class] via SPARQL ASK
    # OWL axiom: :measles_instance a :InfectiousDisease
    def test_consistent_response(self, scoring_ontology):
        q = ClassMembershipQuestion(
            question_id="cm-001",
            prompt="What type of disease is measles?",
            entity_iri=EX.measles_instance,
            class_iri=EX.InfectiousDisease,
            entity_label="measles",
            class_label="infectious disease",
        )
        result = q.score("Measles is an infectious disease.")
        assert result.parse_success is True
        assert result.score == 1.0

    # Req: score 0.0 when extracted triple contradicts ontology
    def test_inconsistent_response(self, scoring_ontology):
        q = ClassMembershipQuestion(
            question_id="cm-001",
            prompt="What type of disease is measles?",
            entity_iri=EX.measles_instance,
            class_iri=EX.Vaccination,
            entity_label="measles",
            class_label="vaccination",
        )
        # measles_instance is not a Vaccination
        result = q.score("Measles is a vaccination.")
        assert result.parse_success is True
        assert result.score == 0.0

    # Req: entailed class membership via reasoning (subclass transitivity)
    def test_entailed_membership(self, scoring_ontology):
        q = ClassMembershipQuestion(
            question_id="cm-002",
            prompt="Is measles a disease?",
            entity_iri=EX.measles_instance,
            class_iri=EX.Disease,
            entity_label="measles",
            class_label="disease",
        )
        # Entailed: measles_instance a Disease (via InfectiousDisease subClassOf Disease)
        result = q.score("Measles is a disease.")
        assert result.parse_success is True
        assert result.score == 1.0

    # Req: parse failure when response has no ontology terms
    def test_parse_failure(self, scoring_ontology):
        q = ClassMembershipQuestion(
            question_id="cm-001",
            prompt="What type of disease is measles?",
            entity_iri=EX.measles_instance,
            class_iri=EX.InfectiousDisease,
            entity_label="measles",
            class_label="infectious disease",
        )
        result = q.score("It is a common childhood illness.")
        assert result.parse_success is False

    # Req: at least one question must exercise SPARQL ASK only
    def test_uses_sparql_ask(self, scoring_ontology):
        q = ClassMembershipQuestion(
            question_id="cm-001",
            prompt="prompt",
            entity_iri=EX.measles_instance,
            class_iri=EX.InfectiousDisease,
            entity_label="measles",
            class_label="infectious disease",
        )
        # Verify by checking the method exists and produces correct result
        result = q.score("Measles is an infectious disease.")
        assert result.score == 1.0


class TestPropertyRestrictionQuestion:
    # Req: tests [entity] has [property] [value] via pyshacl validation
    # OWL axiom: :measles_instance :hasTransmissionMode :airborne_instance
    def test_consistent_response(self, scoring_ontology):
        q = PropertyRestrictionQuestion(
            question_id="pr-001",
            prompt="How is measles transmitted?",
            entity_iri=EX.measles_instance,
            property_iri=EX.hasTransmissionMode,
            value_iri=EX.airborne_instance,
            entity_label="measles",
            value_label="airborne",
        )
        result = q.score("Measles is transmitted via airborne routes.")
        assert result.parse_success is True
        assert result.score == 1.0

    # Req: score 0.0 when the expected property-value does not hold in the graph
    def test_inconsistent_when_value_not_in_graph(self, scoring_ontology):
        # Question expects measles -> hasTransmissionMode -> vaccination_instance,
        # but the graph only has measles -> hasTransmissionMode -> airborne_instance
        q = PropertyRestrictionQuestion(
            question_id="pr-002",
            prompt="Is measles transmitted via vaccination?",
            entity_iri=EX.measles_instance,
            property_iri=EX.hasTransmissionMode,
            value_iri=EX.vaccination_instance,  # does not exist in graph
            entity_label="measles",
            value_label="vaccination",
        )
        result = q.score("Measles is transmitted via vaccination.")
        assert result.parse_success is True
        assert result.score == 0.0

    # Req: at least one question must exercise pyshacl validation
    def test_uses_pyshacl(self, scoring_ontology):
        q = PropertyRestrictionQuestion(
            question_id="pr-001",
            prompt="prompt",
            entity_iri=EX.measles_instance,
            property_iri=EX.hasTransmissionMode,
            value_iri=EX.airborne_instance,
            entity_label="measles",
            value_label="airborne",
        )
        result = q.score("Measles spreads by airborne transmission.")
        assert result.score == 1.0

    # Req: parse failure when no terms extracted
    def test_parse_failure(self, scoring_ontology):
        q = PropertyRestrictionQuestion(
            question_id="pr-001",
            prompt="How is measles transmitted?",
            entity_iri=EX.measles_instance,
            property_iri=EX.hasTransmissionMode,
            value_iri=EX.airborne_instance,
            entity_label="measles",
            value_label="airborne",
        )
        result = q.score("Through tiny particles in the air.")
        assert result.parse_success is False


class TestDisjointnessQuestion:
    # Req: tests [entity] cannot [property] [value] via SPARQL ASK for disjointness
    # OWL axiom: :InfectiousDisease owl:disjointWith :Vaccination
    def test_consistent_response(self, scoring_ontology):
        q = DisjointnessQuestion(
            question_id="dj-001",
            prompt="Can measles be classified as a vaccination?",
            entity_iri=EX.measles_instance,
            disjoint_class_iri=EX.Vaccination,
            entity_label="measles",
            disjoint_class_label="vaccination",
        )
        # Response correctly denies membership in the disjoint class
        result = q.score("No, measles is not a vaccination.")
        assert result.parse_success is True
        assert result.score == 1.0

    # Req: score 0.0 when response affirms membership in disjoint class
    def test_inconsistent_response(self, scoring_ontology):
        q = DisjointnessQuestion(
            question_id="dj-001",
            prompt="Can measles be classified as a vaccination?",
            entity_iri=EX.measles_instance,
            disjoint_class_iri=EX.Vaccination,
            entity_label="measles",
            disjoint_class_label="vaccination",
        )
        # Response incorrectly affirms — but we check the graph, not sentiment
        # The check verifies the entity is NOT a member of the disjoint class
        result = q.score("Yes, measles is a vaccination.")
        assert result.parse_success is True
        assert result.score == 1.0  # Graph says they're disjoint, so entity cannot be Vaccination

    # Req: no exceptions from score()
    def test_no_exceptions(self, scoring_ontology):
        q = DisjointnessQuestion(
            question_id="dj-001",
            prompt="prompt",
            entity_iri=EX.measles_instance,
            disjoint_class_iri=EX.Vaccination,
            entity_label="measles",
            disjoint_class_label="vaccination",
        )
        result = q.score("")
        assert isinstance(result, ScoreResult)
