"""Tests for ontology_client.py — OntologyClient (Model B).

Uses stub ontology and question objects. No Ollama, no real OWL file needed.
Tests that OntologyClient implements ModelClient, generates parseable template
responses, and correctly updates its belief graph.
"""

import rdflib
from rdflib import Namespace, URIRef
from rdflib.namespace import RDF

import pytest

from apollo_eval.model_client import ModelClient
from apollo_eval.ontology import Ontology, ScoreResult
from apollo_eval.ontology_client import OntologyClient, build_sparse_belief_graph
from apollo_eval.question import (
    ClassMembershipQuestion,
    DisjointnessQuestion,
    PropertyRestrictionQuestion,
)


SCENARIO = Namespace("http://example.org/test/")
OBO = Namespace("http://purl.obolibrary.org/obo/")


def _make_stub_ontology(triples=None):
    """Build a minimal Ontology with a small graph for testing."""
    import spacy
    from spacy.matcher import PhraseMatcher

    graph = rdflib.Graph()
    if triples:
        for t in triples:
            graph.add(t)

    nlp = spacy.blank("en")
    matcher = PhraseMatcher(nlp.vocab)
    return Ontology(
        graph=graph,
        nlp=nlp,
        matcher=matcher,
        vocab_labels=[],
        similarity_threshold=1.0,
    )


# --- ABC compliance ---

class TestOntologyClientIsModelClient:
    # Req: OntologyClient implements ModelClient ABC
    def test_is_model_client(self):
        ontology = _make_stub_ontology()
        client = OntologyClient(ontology, [])
        assert isinstance(client, ModelClient)


# --- Template responses ---

class TestClassMembershipResponse:
    # Req: returns affirming template when graph has the membership triple
    def test_affirms_membership_when_in_graph(self):
        triples = [(SCENARIO.dog, RDF.type, SCENARIO.Animal)]
        ontology = _make_stub_ontology(triples)
        q = ClassMembershipQuestion(
            question_id="q1",
            prompt="Is dog an animal?",
            entity_iri=SCENARIO.dog,
            class_iri=SCENARIO.Animal,
            entity_label="dog",
            class_label="animal",
        )
        client = OntologyClient(ontology, [q])
        response = client.complete([], "Is dog an animal?")
        assert "Yes" in response
        assert "dog" in response
        assert "animal" in response

    # Req: returns negating template when graph lacks the membership triple
    def test_denies_membership_when_not_in_graph(self):
        ontology = _make_stub_ontology()  # empty graph
        q = ClassMembershipQuestion(
            question_id="q1",
            prompt="Is dog an animal?",
            entity_iri=SCENARIO.dog,
            class_iri=SCENARIO.Animal,
            entity_label="dog",
            class_label="animal",
        )
        client = OntologyClient(ontology, [q])
        response = client.complete([], "Is dog an animal?")
        assert "No" in response
        assert "not" in response

    # Req: unknown prompt returns fallback
    def test_unknown_prompt_returns_fallback(self):
        ontology = _make_stub_ontology()
        client = OntologyClient(ontology, [])
        response = client.complete([], "Something unknown")
        assert "don't have information" in response


class TestPropertyRestrictionResponse:
    # Req: affirms when graph has the property triple
    def test_affirms_property_when_in_graph(self):
        triples = [(SCENARIO.dog, SCENARIO.has_owner, SCENARIO.alice)]
        ontology = _make_stub_ontology(triples)
        q = PropertyRestrictionQuestion(
            question_id="q2",
            prompt="Does dog have an owner?",
            entity_iri=SCENARIO.dog,
            property_iri=SCENARIO.has_owner,
            value_iri=SCENARIO.alice,
            entity_label="dog",
            value_label="owner",
        )
        client = OntologyClient(ontology, [q])
        response = client.complete([], "Does dog have an owner?")
        assert "Yes" in response

    # Req: denies when graph lacks the property triple
    def test_denies_property_when_not_in_graph(self):
        ontology = _make_stub_ontology()
        q = PropertyRestrictionQuestion(
            question_id="q2",
            prompt="Does dog have an owner?",
            entity_iri=SCENARIO.dog,
            property_iri=SCENARIO.has_owner,
            value_iri=SCENARIO.alice,
            entity_label="dog",
            value_label="owner",
        )
        client = OntologyClient(ontology, [q])
        response = client.complete([], "Does dog have an owner?")
        assert "No" in response
        assert "not" in response.lower() or "does not" in response.lower()


class TestDisjointnessResponse:
    # Req: denies membership in disjoint class when entity is NOT a member
    def test_denies_when_not_member_of_disjoint(self):
        triples = [(SCENARIO.dog, RDF.type, SCENARIO.Animal)]
        ontology = _make_stub_ontology(triples)
        q = DisjointnessQuestion(
            question_id="q3",
            prompt="Can dog be a plant?",
            entity_iri=SCENARIO.dog,
            disjoint_class_iri=SCENARIO.Plant,
            entity_label="dog",
            disjoint_class_label="plant",
        )
        client = OntologyClient(ontology, [q])
        response = client.complete([], "Can dog be a plant?")
        assert "No" in response
        assert "cannot" in response

    # Req: affirms when entity IS a member of the disjoint class
    def test_affirms_when_member_of_disjoint(self):
        triples = [(SCENARIO.dog, RDF.type, SCENARIO.Plant)]
        ontology = _make_stub_ontology(triples)
        q = DisjointnessQuestion(
            question_id="q3",
            prompt="Can dog be a plant?",
            entity_iri=SCENARIO.dog,
            disjoint_class_iri=SCENARIO.Plant,
            entity_label="dog",
            disjoint_class_label="plant",
        )
        client = OntologyClient(ontology, [q])
        response = client.complete([], "Can dog be a plant?")
        assert "Yes" in response


# --- Belief graph independence ---

class TestBeliefGraphIsolation:
    # Req: belief graph is a deep copy, not shared with ontology.graph
    def test_belief_graph_is_independent(self):
        triples = [(SCENARIO.dog, RDF.type, SCENARIO.Animal)]
        ontology = _make_stub_ontology(triples)
        client = OntologyClient(ontology, [])

        # Remove from belief graph
        client.belief_graph.remove((SCENARIO.dog, RDF.type, SCENARIO.Animal))

        # Original ontology graph should be unaffected
        assert (SCENARIO.dog, RDF.type, SCENARIO.Animal) in ontology.graph


# --- Belief updates ---

class TestBeliefUpdateClassMembership:
    # Req: add triple when A affirms membership B lacks
    def test_add_when_a_affirms_and_graph_lacks(self):
        ontology = _make_stub_ontology()  # empty graph
        q = ClassMembershipQuestion(
            question_id="q1", prompt="test",
            entity_iri=SCENARIO.dog, class_iri=SCENARIO.Animal,
            entity_label="dog", class_label="animal",
        )
        client = OntologyClient(ontology, [q])

        update = client.update_belief(q, a_is_negated=False)  # A affirms
        assert update is not None
        assert update["action"] == "add"
        assert (SCENARIO.dog, RDF.type, SCENARIO.Animal) in client.belief_graph

    # Req: retract triple when A denies membership B has
    def test_retract_when_a_denies_and_graph_has(self):
        triples = [(SCENARIO.dog, RDF.type, SCENARIO.Animal)]
        ontology = _make_stub_ontology(triples)
        q = ClassMembershipQuestion(
            question_id="q1", prompt="test",
            entity_iri=SCENARIO.dog, class_iri=SCENARIO.Animal,
            entity_label="dog", class_label="animal",
        )
        client = OntologyClient(ontology, [q])

        update = client.update_belief(q, a_is_negated=True)  # A denies
        assert update is not None
        assert update["action"] == "retract"
        assert (SCENARIO.dog, RDF.type, SCENARIO.Animal) not in client.belief_graph

    # Req: no update when A and B agree
    def test_no_update_when_aligned(self):
        triples = [(SCENARIO.dog, RDF.type, SCENARIO.Animal)]
        ontology = _make_stub_ontology(triples)
        q = ClassMembershipQuestion(
            question_id="q1", prompt="test",
            entity_iri=SCENARIO.dog, class_iri=SCENARIO.Animal,
            entity_label="dog", class_label="animal",
        )
        client = OntologyClient(ontology, [q])

        update = client.update_belief(q, a_is_negated=False)  # A affirms, graph has it
        assert update is None


class TestBeliefUpdatePropertyRestriction:
    # Req: add property triple when A affirms and graph lacks
    def test_add_property(self):
        ontology = _make_stub_ontology()
        q = PropertyRestrictionQuestion(
            question_id="q2", prompt="test",
            entity_iri=SCENARIO.dog, property_iri=SCENARIO.has_owner,
            value_iri=SCENARIO.alice, entity_label="dog", value_label="owner",
        )
        client = OntologyClient(ontology, [q])

        update = client.update_belief(q, a_is_negated=False)
        assert update is not None
        assert update["action"] == "add"
        assert (SCENARIO.dog, SCENARIO.has_owner, SCENARIO.alice) in client.belief_graph

    # Req: retract property triple when A denies and graph has
    def test_retract_property(self):
        triples = [(SCENARIO.dog, SCENARIO.has_owner, SCENARIO.alice)]
        ontology = _make_stub_ontology(triples)
        q = PropertyRestrictionQuestion(
            question_id="q2", prompt="test",
            entity_iri=SCENARIO.dog, property_iri=SCENARIO.has_owner,
            value_iri=SCENARIO.alice, entity_label="dog", value_label="owner",
        )
        client = OntologyClient(ontology, [q])

        update = client.update_belief(q, a_is_negated=True)
        assert update is not None
        assert update["action"] == "retract"


class TestBeliefUpdateDisjointness:
    # Req: add type triple when A says entity CAN be disjoint class
    def test_add_disjoint_type(self):
        ontology = _make_stub_ontology()
        q = DisjointnessQuestion(
            question_id="q3", prompt="test",
            entity_iri=SCENARIO.dog, disjoint_class_iri=SCENARIO.Plant,
            entity_label="dog", disjoint_class_label="plant",
        )
        client = OntologyClient(ontology, [q])

        update = client.update_belief(q, a_is_negated=False)  # A says "Yes, can"
        assert update is not None
        assert update["action"] == "add"
        assert (SCENARIO.dog, RDF.type, SCENARIO.Plant) in client.belief_graph

    # Req: no update when A correctly says entity cannot be disjoint class
    def test_no_update_when_correctly_disjoint(self):
        ontology = _make_stub_ontology()
        q = DisjointnessQuestion(
            question_id="q3", prompt="test",
            entity_iri=SCENARIO.dog, disjoint_class_iri=SCENARIO.Plant,
            entity_label="dog", disjoint_class_label="plant",
        )
        client = OntologyClient(ontology, [q])

        update = client.update_belief(q, a_is_negated=True)  # A says "No, cannot"
        assert update is None


# --- Sparse belief graph ---

TBOX_NS = Namespace("http://example.org/tbox/")

class TestBuildSparseBeliefGraph:
    # Req: keeps non-scenario triples (TBox)
    def test_keeps_tbox_triples(self):
        graph = rdflib.Graph()
        graph.add((TBOX_NS.Animal, RDF.type, TBOX_NS.Class))
        graph.add((TBOX_NS.Dog, TBOX_NS.subClassOf, TBOX_NS.Animal))
        # Scenario instance
        graph.add((SCENARIO.dog, RDF.type, TBOX_NS.Animal))

        sparse = build_sparse_belief_graph(graph, scenario_ns=str(SCENARIO))
        assert (TBOX_NS.Animal, RDF.type, TBOX_NS.Class) in sparse
        assert (TBOX_NS.Dog, TBOX_NS.subClassOf, TBOX_NS.Animal) in sparse

    # Req: keeps direct rdf:type for scenario instances
    def test_keeps_direct_scenario_types(self):
        graph = rdflib.Graph()
        graph.add((SCENARIO.dog, RDF.type, TBOX_NS.Animal))

        sparse = build_sparse_belief_graph(graph, scenario_ns=str(SCENARIO))
        assert (SCENARIO.dog, RDF.type, TBOX_NS.Animal) in sparse

    # Req: strips property assertions between scenario instances
    def test_strips_scenario_property_assertions(self):
        graph = rdflib.Graph()
        graph.add((SCENARIO.dog, RDF.type, TBOX_NS.Animal))
        graph.add((SCENARIO.dog, TBOX_NS.has_owner, SCENARIO.alice))  # property assertion

        sparse = build_sparse_belief_graph(graph, scenario_ns=str(SCENARIO))
        assert (SCENARIO.dog, RDF.type, TBOX_NS.Animal) in sparse
        assert (SCENARIO.dog, TBOX_NS.has_owner, SCENARIO.alice) not in sparse

    # Req: strips property assertions to non-scenario objects too
    def test_strips_scenario_to_tbox_properties(self):
        graph = rdflib.Graph()
        graph.add((SCENARIO.dog, RDF.type, TBOX_NS.Animal))
        graph.add((SCENARIO.dog, TBOX_NS.occurs_in, TBOX_NS.Ecosystem))

        sparse = build_sparse_belief_graph(graph, scenario_ns=str(SCENARIO))
        assert (SCENARIO.dog, TBOX_NS.occurs_in, TBOX_NS.Ecosystem) not in sparse


class TestOntologyClientSparseMode:
    SCENARIO_NS = str(SCENARIO)

    # Req: sparse=True produces fewer triples than sparse=False
    def test_sparse_has_fewer_triples(self):
        triples = [
            (SCENARIO.dog, RDF.type, TBOX_NS.Animal),
            (SCENARIO.dog, TBOX_NS.has_owner, SCENARIO.alice),
            (TBOX_NS.Animal, RDF.type, TBOX_NS.Class),
        ]
        ontology = _make_stub_ontology(triples)

        full_client = OntologyClient(ontology, [])
        sparse_client = OntologyClient(ontology, [], sparse=True, scenario_ns=self.SCENARIO_NS)

        assert len(sparse_client.belief_graph) < len(full_client.belief_graph)

    # Req: sparse B denies property assertions it doesn't have
    def test_sparse_denies_missing_properties(self):
        triples = [
            (SCENARIO.dog, RDF.type, TBOX_NS.Animal),
            (SCENARIO.dog, SCENARIO.has_owner, SCENARIO.alice),
        ]
        ontology = _make_stub_ontology(triples)
        q = PropertyRestrictionQuestion(
            question_id="q1", prompt="Does dog have owner?",
            entity_iri=SCENARIO.dog, property_iri=SCENARIO.has_owner,
            value_iri=SCENARIO.alice, entity_label="dog", value_label="owner",
        )

        sparse_client = OntologyClient(ontology, [q], sparse=True, scenario_ns=self.SCENARIO_NS)
        response = sparse_client.complete([], "Does dog have owner?")
        assert "No" in response
        assert "not" in response.lower() or "does not" in response.lower()

    # Req: sparse B still affirms direct types
    def test_sparse_affirms_direct_types(self):
        triples = [(SCENARIO.dog, RDF.type, TBOX_NS.Animal)]
        ontology = _make_stub_ontology(triples)
        q = ClassMembershipQuestion(
            question_id="q1", prompt="Is dog an animal?",
            entity_iri=SCENARIO.dog, class_iri=TBOX_NS.Animal,
            entity_label="dog", class_label="animal",
        )

        sparse_client = OntologyClient(ontology, [q], sparse=True, scenario_ns=self.SCENARIO_NS)
        response = sparse_client.complete([], "Is dog an animal?")
        assert "Yes" in response
