import rdflib
import spacy
from rdflib import Literal
from rdflib.namespace import RDFS, SKOS
from spacy.matcher import PhraseMatcher

from apollo_eval.ontology import Ontology

# oboInOwl namespace used by OBO ontologies for synonym annotations
OBOINOWL = rdflib.Namespace("http://www.geneontology.org/formats/oboInOwl#")

# Annotation properties to extract labels from
_LABEL_PREDICATES = [
    RDFS.label,
    SKOS.prefLabel,
    SKOS.altLabel,
    OBOINOWL.hasExactSynonym,
]


class OntologyVocabularyBuilder:
    """Builds a spaCy nlp pipeline and PhraseMatcher from an expanded RDF graph.

    Uses en_core_web_sm as the base model — lightweight and sufficient for
    PhraseMatcher-based NER against a controlled vocabulary. No transformer
    needed since we are doing exact phrase matching, not learned NER.
    """

    def __init__(self, graph: rdflib.Graph):
        self.graph = graph

    def build(self) -> Ontology:
        labels = self._extract_labels()
        # en_core_web_sm provides tokenizer, tagger, parser, and NER — needed
        # for dependency-based negation detection in response scoring.
        # PhraseMatcher works the same way on top of the full pipeline.
        nlp = spacy.load("en_core_web_sm")
        matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

        for label in labels:
            nlp.vocab.strings.add(label)

        if labels:
            patterns = [nlp.make_doc(label) for label in labels]
            matcher.add("ONTOLOGY_TERM", patterns)

        return Ontology(graph=self.graph, nlp=nlp, matcher=matcher)

    def _extract_labels(self) -> list[str]:
        """Extract all label strings from the graph via annotation properties."""
        labels = set()
        for predicate in _LABEL_PREDICATES:
            for _, _, obj in self.graph.triples((None, predicate, None)):
                if isinstance(obj, Literal):
                    text = str(obj).strip()
                    if text:
                        labels.add(text.lower())
        return sorted(labels)
