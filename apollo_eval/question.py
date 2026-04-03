from abc import ABC, abstractmethod

import rdflib
from rdflib import Namespace, URIRef
from rdflib.namespace import RDF

from apollo_eval.ontology import Ontology, ScoreResult

SH = Namespace("http://www.w3.org/ns/shacl#")

# Tokens that signal negation in a response. Checked both via spaCy dependency
# parsing (dep_ == "neg") and lexical lookup for cases the parser misses.
_NEGATION_TOKENS = frozenset({
    "not", "no", "never", "cannot", "can't", "isn't", "aren't",
    "doesn't", "don't", "won't", "wouldn't", "shouldn't", "couldn't",
    "neither", "nor", "nothing", "none", "nowhere",
})


class Question(ABC):
    """Base class for ontology-grounded evaluation questions.

    The class-level `ontology` attribute is set once during preprocessing
    via `Question.ontology = ontology` and shared by all subclasses.

    Scoring pipeline per response:
    1. Extract ontology-grounded terms via PhraseMatcher (parse gate)
    2. Detect whether the response negates the relationship
    3. Check the ontological fact against the expanded graph
    4. Combine graph truth with response polarity for final score
    """

    ontology: Ontology = None

    question_id: str
    prompt: str

    def score(self, response: str) -> ScoreResult:
        """Score a response for consistency with the ontology.

        Returns ScoreResult with parse_success=False if no terms could be
        extracted. Never raises exceptions.
        """
        terms, fuzz = self._extract_terms(response)
        if not terms:
            return ScoreResult(
                question_id=self.question_id,
                parse_success=False,
                score=0.0,
                fuzz=None,
            )
        is_negated = self._detect_negation(response)
        consistent = self._check(terms, is_negated)
        return ScoreResult(
            question_id=self.question_id,
            parse_success=True,
            score=1.0 if consistent else 0.0,
            fuzz=fuzz,
        )

    def _extract_terms(self, response: str) -> tuple[list[str], bool | None]:
        """Extract ontology-grounded terms from response text.

        Two-stage extraction:
        1. Exact match via PhraseMatcher (always runs)
        2. Similarity fallback (only when threshold < 1.0 AND stage 1 found nothing)

        Returns (terms, fuzz) where fuzz is False for exact match, True for
        similarity fallback, or None if no terms were found.
        """
        doc = self.ontology.nlp(response)

        # Stage 1: Exact PhraseMatcher
        matches = self.ontology.matcher(doc)
        matched_indices = set()
        seen = set()
        terms = []
        for _, start, end in matches:
            text = doc[start:end].text.lower()
            if text not in seen:
                seen.add(text)
                terms.append(text)
            for i in range(start, end):
                matched_indices.add(i)

        if terms:
            return terms, False

        # Stage 2: Similarity fallback (only when exact match found nothing)
        threshold = self.ontology.similarity_threshold
        if threshold < 1.0:
            terms = self._similarity_fallback(doc, matched_indices, seen, threshold)
            if terms:
                return terms, True

        return [], None

    def _similarity_fallback(
        self, doc, matched_indices: set, seen: set, threshold: float
    ) -> list[str]:
        """Find ontology terms via vector similarity for unmatched tokens.

        For single-word labels: best token-to-token cosine similarity.
        For multi-word labels: sliding-window Doc-to-Doc similarity.
        """
        vocab_docs = self.ontology.get_vocab_docs()
        terms = []

        for label, label_doc in vocab_docs.items():
            if label in seen:
                continue

            best_sim = 0.0

            if len(label_doc) == 1:
                for i, token in enumerate(doc):
                    if i in matched_indices or not token.has_vector:
                        continue
                    sim = token.similarity(label_doc[0])
                    if sim > best_sim:
                        best_sim = sim
            else:
                label_len = len(label_doc)
                for start in range(len(doc) - label_len + 1):
                    if any(j in matched_indices for j in range(start, start + label_len)):
                        continue
                    span = doc[start:start + label_len]
                    if span.has_vector and label_doc.has_vector:
                        sim = span.similarity(label_doc)
                        if sim > best_sim:
                            best_sim = sim

            if best_sim >= threshold:
                terms.append(label)
                seen.add(label)

        return terms

    def _detect_negation(self, response: str) -> bool:
        """Detect whether the response contains negation.

        Uses two signals:
        1. spaCy dependency parser: tokens with dep_=="neg" (e.g., "not" modifying a verb)
        2. Lexical fallback: known negation tokens for cases the parser misses

        This determines response polarity — whether the response affirms or
        denies the relationship being tested.
        """
        doc = self.ontology.nlp(response)
        for token in doc:
            if token.dep_ == "neg":
                return True
            if token.text.lower() in _NEGATION_TOKENS:
                return True
        return False

    @abstractmethod
    def _check(self, extracted_terms: list[str], is_negated: bool) -> bool:
        """Check consistency of the response against the ontology.

        Combines the graph truth with the response polarity (is_negated)
        to determine if the response is consistent.

        Implemented by concrete subclasses using SPARQL ASK or pyshacl.
        """
        ...


class ClassMembershipQuestion(Question):
    """Tests [entity] is a [class] — class membership entailment via SPARQL ASK.

    OWL axiom tested: rdf:type assertion (possibly entailed via subclass reasoning).
    Checking method: SPARQL ASK only.

    Scoring logic:
    - graph says entity IS a class + response affirms → 1.0
    - graph says entity IS a class + response negates → 0.0
    - graph says entity NOT a class + response negates → 1.0
    - graph says entity NOT a class + response affirms → 0.0
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

    def _check(self, extracted_terms: list[str], is_negated: bool) -> bool:
        """SPARQL ASK + negation: is the response consistent with membership?"""
        result = self.ontology.graph.query(
            "ASK { ?entity a ?cls }",
            initBindings={"entity": self.entity_iri, "cls": self.class_iri},
        )
        graph_says_member = bool(result.askAnswer)
        response_affirms = not is_negated
        return graph_says_member == response_affirms


class PropertyRestrictionQuestion(Question):
    """Tests [entity] has [property] [value] — property restriction via pyshacl.

    OWL axiom tested: property assertion on an individual.
    Checking method: pyshacl validation against a dynamically constructed SHACL shape.

    Scoring logic:
    - graph has the triple + response affirms → 1.0
    - graph has the triple + response negates → 0.0
    - graph lacks the triple + response negates → 1.0
    - graph lacks the triple + response affirms → 0.0
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

    def _check(self, extracted_terms: list[str], is_negated: bool) -> bool:
        """pyshacl validation + negation: is the response consistent?"""
        import pyshacl

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
            inference="none",
        )
        response_affirms = not is_negated
        return conforms == response_affirms


class DisjointnessQuestion(Question):
    """Tests [entity] cannot be a [class] — disjointness constraint via SPARQL ASK.

    OWL axiom tested: owl:disjointWith between the entity's class and the target class.
    Checking method: SPARQL ASK — checks whether the entity is a member of the
    disjoint class.

    Scoring logic (note: question asks about disjointness, so negation = agreement):
    - entity NOT in disjoint class + response negates → 1.0 ("No, it cannot")
    - entity NOT in disjoint class + response affirms → 0.0 ("Yes, it can")
    - entity IN disjoint class + response affirms → 1.0
    - entity IN disjoint class + response negates → 0.0
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

    def _check(self, extracted_terms: list[str], is_negated: bool) -> bool:
        """SPARQL ASK + negation: is the response consistent with disjointness?"""
        is_member = self.ontology.graph.query(
            "ASK { ?entity a ?cls }",
            initBindings={
                "entity": self.entity_iri,
                "cls": self.disjoint_class_iri,
            },
        )
        entity_not_member = not bool(is_member.askAnswer)
        # Disjointness questions expect negation when entity is not a member:
        # "Can X be a Y?" → "No" is consistent when X cannot be Y
        return entity_not_member == is_negated
