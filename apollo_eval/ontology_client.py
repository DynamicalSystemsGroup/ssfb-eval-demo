"""OWL-based symbolic operator (Model B) for operator comparison.

OntologyClient implements ModelClient, answering questions by querying a mutable
belief graph via SPARQL/pyshacl and returning template natural-language responses.
The belief graph starts as either a full or sparse copy of the ground-truth
ontology graph and can be updated to imitate Model A's assertions (online
learning / system identification).

Sparse mode: B starts with the TBox (class hierarchy, disjointness) and direct
rdf:type assertions for scenario instances, but no property assertions and no
entailed types. This forces B to learn relational structure from A rather than
just confirming what it already knows.
"""

import copy

import rdflib
from rdflib import Namespace, URIRef
from rdflib.namespace import RDF

from apollo_eval.model_client import ModelClient
from apollo_eval.ontology import Ontology
from apollo_eval.question import (
    ClassMembershipQuestion,
    DisjointnessQuestion,
    PropertyRestrictionQuestion,
    Question,
)

SH = Namespace("http://www.w3.org/ns/shacl#")
SCENARIO_NS = "http://example.org/scenario/measles_epidemic/"


def build_sparse_belief_graph(
    full_graph: rdflib.Graph,
    scenario_ns: str = SCENARIO_NS,
) -> rdflib.Graph:
    """Build a sparse belief graph: TBox + direct scenario types only.

    Keeps:
    - All triples NOT involving scenario instances (the TBox / upper ontology)
    - Direct rdf:type assertions for scenario instances

    Strips:
    - Property assertions between scenario instances (relational structure)
    - Entailed rdf:type triples for scenario instances (from OWL RL reasoning)

    The result is a graph where B knows entities exist and their immediate types
    but must learn relational structure and subsumption-entailed types from A.
    """
    sparse = rdflib.Graph()

    # Collect direct types: triples explicitly added by add_scenario_instances()
    # These are the rdf:type triples where the object is NOT itself a scenario IRI
    # (entailed types have the same form but were added by reasoning, not assertion)
    #
    # Strategy: copy ALL non-scenario triples (TBox), then selectively add back
    # only the scenario rdf:type triples that use non-scenario class IRIs as objects.

    for s, p, o in full_graph:
        s_str = str(s)
        o_str = str(o) if isinstance(o, URIRef) else ""

        if not s_str.startswith(scenario_ns):
            # Non-scenario triple — part of the TBox, keep it
            sparse.add((s, p, o))
        elif p == RDF.type and not o_str.startswith(scenario_ns):
            # Scenario instance direct type — keep it
            sparse.add((s, p, o))
        # else: scenario property assertion or entailed type — strip it

    return sparse


def strip_entailed_types(
    sparse_graph: rdflib.Graph,
    direct_types: dict[URIRef, URIRef],
    scenario_ns: str = SCENARIO_NS,
) -> rdflib.Graph:
    """Further strip entailed rdf:type from scenario instances.

    After build_sparse_belief_graph, scenario instances may still have entailed
    types (from OWL RL reasoning that ran before scenario instances were added).
    This function removes all scenario rdf:type triples EXCEPT those in
    direct_types mapping {entity_iri: class_iri}.
    """
    to_remove = []
    for s, p, o in sparse_graph:
        if (str(s).startswith(scenario_ns)
                and p == RDF.type
                and direct_types.get(s) != o):
            to_remove.append((s, p, o))

    for triple in to_remove:
        sparse_graph.remove(triple)

    return sparse_graph


class OntologyClient(ModelClient):
    """Symbolic operator that answers questions from an OWL belief graph.

    Implements the ModelClient ABC so it is interchangeable with OllamaClient.
    Internally resolves prompts to structured queries via a Question registry,
    queries its own belief_graph, and returns template NL responses that are
    parseable by the existing Question.score() pipeline.

    sparse=True starts B with minimal knowledge: TBox + direct instance types
    only, no property assertions or entailed types. This creates a rich initial
    divergence surface where B must learn from A.
    """

    def __init__(
        self,
        ontology: Ontology,
        questions: list[Question],
        sparse: bool = False,
        scenario_ns: str = SCENARIO_NS,
    ):
        self.ontology = ontology
        self.sparse = sparse
        if sparse:
            self.belief_graph = build_sparse_belief_graph(
                ontology.graph, scenario_ns=scenario_ns,
            )
        else:
            self.belief_graph = copy.deepcopy(ontology.graph)
        self.prompt_to_question: dict[str, Question] = {
            q.prompt: q for q in questions
        }

    def complete(self, history: list[tuple[str, str]], prompt: str) -> str:
        """Return a template NL response by querying the belief graph."""
        question = self.prompt_to_question.get(prompt)
        if question is None:
            return "I don't have information about that."
        return self._answer_from_graph(question)

    def _answer_from_graph(self, question: Question) -> str:
        """Dispatch by question type, query belief_graph, return template NL."""
        if isinstance(question, ClassMembershipQuestion):
            return self._answer_class_membership(question)
        elif isinstance(question, PropertyRestrictionQuestion):
            return self._answer_property_restriction(question)
        elif isinstance(question, DisjointnessQuestion):
            return self._answer_disjointness(question)
        return "I don't have information about that."

    def _answer_class_membership(self, q: ClassMembershipQuestion) -> str:
        result = self.belief_graph.query(
            "ASK { ?entity a ?cls }",
            initBindings={"entity": q.entity_iri, "cls": q.class_iri},
        )
        is_member = bool(result.askAnswer)
        if is_member:
            return f"Yes, {q.entity_label} is a {q.class_label}."
        return f"No, {q.entity_label} is not a {q.class_label}."

    def _answer_property_restriction(self, q: PropertyRestrictionQuestion) -> str:
        import pyshacl

        shapes = rdflib.Graph()
        shape_node = rdflib.BNode()
        prop_shape = rdflib.BNode()
        shapes.add((shape_node, RDF.type, SH.NodeShape))
        shapes.add((shape_node, SH.targetNode, q.entity_iri))
        shapes.add((shape_node, SH.property, prop_shape))
        shapes.add((prop_shape, SH.path, q.property_iri))
        shapes.add((prop_shape, SH.hasValue, q.value_iri))
        shapes.add((prop_shape, SH.minCount, rdflib.Literal(1)))

        conforms, _, _ = pyshacl.validate(
            data_graph=self.belief_graph,
            shacl_graph=shapes,
            inference="none",
        )
        if conforms:
            return f"Yes, {q.entity_label} has {q.value_label}."
        return f"No, {q.entity_label} does not have {q.value_label}."

    def _answer_disjointness(self, q: DisjointnessQuestion) -> str:
        result = self.belief_graph.query(
            "ASK { ?entity a ?cls }",
            initBindings={
                "entity": q.entity_iri,
                "cls": q.disjoint_class_iri,
            },
        )
        is_member = bool(result.askAnswer)
        if is_member:
            return f"Yes, {q.entity_label} can be a {q.disjoint_class_label}."
        return f"No, {q.entity_label} cannot be a {q.disjoint_class_label}."

    def update_belief(
        self, question: Question, a_is_negated: bool
    ) -> dict | None:
        """Update belief graph to imitate A's assertion.

        Compares A's polarity (is_negated) with B's current graph state.
        If they disagree, modifies the belief graph and returns a record
        of the change. Returns None if no update was needed.

        a_is_negated: whether A's response contained negation (from Question._detect_negation)
        """
        if isinstance(question, ClassMembershipQuestion):
            return self._update_class_membership(question, a_is_negated)
        elif isinstance(question, PropertyRestrictionQuestion):
            return self._update_property_restriction(question, a_is_negated)
        elif isinstance(question, DisjointnessQuestion):
            return self._update_disjointness(question, a_is_negated)
        return None

    def _update_class_membership(
        self, q: ClassMembershipQuestion, a_is_negated: bool
    ) -> dict | None:
        triple = (q.entity_iri, RDF.type, q.class_iri)
        graph_has = triple in self.belief_graph
        a_affirms = not a_is_negated

        if a_affirms and not graph_has:
            self.belief_graph.add(triple)
            return {"action": "add", "triple": tuple(str(t) for t in triple)}
        elif not a_affirms and graph_has:
            self.belief_graph.remove(triple)
            return {"action": "retract", "triple": tuple(str(t) for t in triple)}
        return None

    def _update_property_restriction(
        self, q: PropertyRestrictionQuestion, a_is_negated: bool
    ) -> dict | None:
        triple = (q.entity_iri, q.property_iri, q.value_iri)
        graph_has = triple in self.belief_graph
        a_affirms = not a_is_negated

        if a_affirms and not graph_has:
            self.belief_graph.add(triple)
            return {"action": "add", "triple": tuple(str(t) for t in triple)}
        elif not a_affirms and graph_has:
            self.belief_graph.remove(triple)
            return {"action": "retract", "triple": tuple(str(t) for t in triple)}
        return None

    def _update_disjointness(
        self, q: DisjointnessQuestion, a_is_negated: bool
    ) -> dict | None:
        triple = (q.entity_iri, RDF.type, q.disjoint_class_iri)
        graph_has = triple in self.belief_graph

        # Disjointness questions: "Can X be a Y?"
        # a_is_negated=True means A says "No, cannot" (expected for disjoint)
        # a_is_negated=False means A says "Yes, can" (unexpected)
        a_says_can = not a_is_negated

        if a_says_can and not graph_has:
            self.belief_graph.add(triple)
            return {"action": "add", "triple": tuple(str(t) for t in triple)}
        elif not a_says_can and graph_has:
            self.belief_graph.remove(triple)
            return {"action": "retract", "triple": tuple(str(t) for t in triple)}
        return None
