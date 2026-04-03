from abc import ABC, abstractmethod

import rdflib
from rdflib import Namespace, URIRef
from rdflib.namespace import RDF, SH

from apollo_eval.ontology import Ontology, ScoreResult

SH = Namespace("http://www.w3.org/ns/shacl#")


class Question(ABC):
    """Base class for ontology-grounded evaluation questions.

    The class-level `ontology` attribute is set once during preprocessing
    via `Question.ontology = ontology` and shared by all subclasses.

    Each concrete subclass implements `_check()` to validate extracted terms
    against the ontology using SPARQL ASK or pyshacl.
    """

    ontology: Ontology = None

    question_id: str
    prompt: str

    def score(self, response: str) -> ScoreResult:
        """Score a response for consistency with the ontology.

        Returns ScoreResult with parse_success=False if no terms could be
        extracted. Never raises exceptions.
        """
        terms = self._extract_terms(response)
        if not terms:
            return ScoreResult(
                question_id=self.question_id,
                parse_success=False,
                score=0.0,
            )
        consistent = self._check(terms)
        return ScoreResult(
            question_id=self.question_id,
            parse_success=True,
            score=1.0 if consistent else 0.0,
        )

    def _extract_terms(self, response: str) -> list[str]:
        """Extract ontology-grounded terms from response text.

        Uses spaCy PhraseMatcher for NER against the ontology's controlled
        vocabulary. This is a grounding step, not a similarity step.
        """
        doc = self.ontology.nlp(response)
        matches = self.ontology.matcher(doc)
        seen = set()
        terms = []
        for _, start, end in matches:
            text = doc[start:end].text.lower()
            if text not in seen:
                seen.add(text)
                terms.append(text)
        return terms

    @abstractmethod
    def _check(self, extracted_terms: list[str]) -> bool:
        """Check extracted terms for consistency against the ontology.

        Implemented by concrete subclasses using SPARQL ASK or pyshacl.
        Returns True if consistent, False if contradicts.
        """
        ...


class ClassMembershipQuestion(Question):
    """Tests [entity] is a [class] — class membership entailment via SPARQL ASK.

    OWL axiom tested: rdf:type assertion (possibly entailed via subclass reasoning).
    Checking method: SPARQL ASK only.
    """

    def __init__(
        self,
        question_id: str,
        prompt: str,
        entity_iri: URIRef,
        class_iri: URIRef,
        entity_label: str,
        class_label: str,
    ):
        self.question_id = question_id
        self.prompt = prompt
        self.entity_iri = entity_iri
        self.class_iri = class_iri
        self.entity_label = entity_label
        self.class_label = class_label

    def _check(self, extracted_terms: list[str]) -> bool:
        """SPARQL ASK: does the entity belong to the expected class?"""
        result = self.ontology.graph.query(
            "ASK { ?entity a ?cls }",
            initBindings={"entity": self.entity_iri, "cls": self.class_iri},
        )
        return bool(result.askAnswer)


class PropertyRestrictionQuestion(Question):
    """Tests [entity] has [property] [value] — property restriction via pyshacl.

    OWL axiom tested: property assertion on an individual.
    Checking method: pyshacl validation against a dynamically constructed SHACL shape.
    """

    def __init__(
        self,
        question_id: str,
        prompt: str,
        entity_iri: URIRef,
        property_iri: URIRef,
        value_iri: URIRef,
        entity_label: str,
        value_label: str,
    ):
        self.question_id = question_id
        self.prompt = prompt
        self.entity_iri = entity_iri
        self.property_iri = property_iri
        self.value_iri = value_iri
        self.entity_label = entity_label
        self.value_label = value_label

    def _check(self, extracted_terms: list[str]) -> bool:
        """pyshacl validation: does the entity have the expected property value?

        Constructs a SHACL NodeShape requiring the entity to have the expected
        property pointing to the expected value, then validates the data graph.
        """
        import pyshacl

        # Build a SHACL shapes graph requiring entity -> property -> value
        shapes = rdflib.Graph()
        shape_node = rdflib.BNode()
        prop_shape = rdflib.BNode()
        shapes.add((shape_node, RDF.type, SH.NodeShape))
        shapes.add((shape_node, SH.targetNode, self.entity_iri))
        shapes.add((shape_node, SH.property, prop_shape))
        shapes.add((prop_shape, SH.path, self.property_iri))
        shapes.add((prop_shape, SH.hasValue, self.value_iri))
        shapes.add((prop_shape, SH.minCount, rdflib.Literal(1)))

        conforms, _, _ = pyshacl.validate(
            data_graph=self.ontology.graph,
            shacl_graph=shapes,
            inference="none",  # reasoning already applied
        )
        return conforms


class DisjointnessQuestion(Question):
    """Tests [entity] cannot be a [class] — disjointness constraint via SPARQL ASK.

    OWL axiom tested: owl:disjointWith between the entity's class and the target class.
    Checking method: SPARQL ASK — confirms the entity is NOT a member of the disjoint class.
    """

    def __init__(
        self,
        question_id: str,
        prompt: str,
        entity_iri: URIRef,
        disjoint_class_iri: URIRef,
        entity_label: str,
        disjoint_class_label: str,
    ):
        self.question_id = question_id
        self.prompt = prompt
        self.entity_iri = entity_iri
        self.disjoint_class_iri = disjoint_class_iri
        self.entity_label = entity_label
        self.disjoint_class_label = disjoint_class_label

    def _check(self, extracted_terms: list[str]) -> bool:
        """SPARQL ASK: confirm the entity is NOT a member of the disjoint class.

        Returns True (consistent) if the entity does not belong to the disjoint
        class, False (inconsistent) if it does.
        """
        is_member = self.ontology.graph.query(
            "ASK { ?entity a ?cls }",
            initBindings={
                "entity": self.entity_iri,
                "cls": self.disjoint_class_iri,
            },
        )
        # Consistent means the entity is NOT in the disjoint class
        return not bool(is_member.askAnswer)
