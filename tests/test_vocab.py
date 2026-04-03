import rdflib
from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDFS, SKOS

from apollo_eval.ontology import Ontology
from apollo_eval.vocab import OntologyVocabularyBuilder

EX = Namespace("http://example.org/")
OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")


def _build_test_graph():
    """Small hand-built RDF graph with various label annotations."""
    g = rdflib.Graph()
    g.bind("ex", EX)
    g.bind("skos", SKOS)
    # rdfs:label
    g.add((EX.Measles, RDFS.label, Literal("measles")))
    # skos:prefLabel
    g.add((EX.Vaccination, SKOS.prefLabel, Literal("vaccination")))
    # skos:altLabel
    g.add((EX.Vaccination, SKOS.altLabel, Literal("immunization")))
    # oboInOwl:hasExactSynonym
    g.add((EX.Measles, OBOINOWL.hasExactSynonym, Literal("rubeola")))
    # Multi-word label for PhraseMatcher testing
    g.add((EX.InfectiousDisease, RDFS.label, Literal("infectious disease")))
    return g


class TestOntologyVocabularyBuilder:
    # Req: extracts rdfs:label values and adds them to nlp vocab
    def test_rdfs_label_in_vocab(self):
        g = _build_test_graph()
        ont = OntologyVocabularyBuilder(g).build()
        assert "measles" in ont.nlp.vocab.strings

    # Req: extracts skos:prefLabel values
    def test_skos_preflabel_in_vocab(self):
        g = _build_test_graph()
        ont = OntologyVocabularyBuilder(g).build()
        assert "vaccination" in ont.nlp.vocab.strings

    # Req: extracts skos:altLabel values
    def test_skos_altlabel_in_vocab(self):
        g = _build_test_graph()
        ont = OntologyVocabularyBuilder(g).build()
        assert "immunization" in ont.nlp.vocab.strings

    # Req: extracts oboInOwl:hasExactSynonym values
    def test_exact_synonym_in_vocab(self):
        g = _build_test_graph()
        ont = OntologyVocabularyBuilder(g).build()
        assert "rubeola" in ont.nlp.vocab.strings

    # Req: returns a fully constructed Ontology instance
    def test_returns_ontology_instance(self):
        g = _build_test_graph()
        ont = OntologyVocabularyBuilder(g).build()
        assert isinstance(ont, Ontology)
        assert ont.graph is g

    # Req: multi-word labels added as PhraseMatcher patterns for span recognition
    def test_phrase_matcher_finds_multi_word_label(self):
        g = _build_test_graph()
        ont = OntologyVocabularyBuilder(g).build()
        doc = ont.nlp("The patient has an infectious disease.")
        matches = ont.matcher(doc)
        matched_texts = [doc[start:end].text for _, start, end in matches]
        assert "infectious disease" in matched_texts

    # Req: single-word labels are also findable via PhraseMatcher
    def test_phrase_matcher_finds_single_word_label(self):
        g = _build_test_graph()
        ont = OntologyVocabularyBuilder(g).build()
        doc = ont.nlp("The treatment is vaccination.")
        matches = ont.matcher(doc)
        matched_texts = [doc[start:end].text for _, start, end in matches]
        assert "vaccination" in matched_texts

    # Req: empty graph produces valid Ontology with no matcher patterns
    def test_empty_graph(self):
        g = rdflib.Graph()
        ont = OntologyVocabularyBuilder(g).build()
        assert isinstance(ont, Ontology)
        doc = ont.nlp("some random text")
        matches = ont.matcher(doc)
        assert len(matches) == 0
