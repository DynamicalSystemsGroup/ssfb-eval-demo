import rdflib
from rdflib import Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL

import pytest

from apollo_eval.ontology import Ontology
from apollo_eval.ontology_loader import OntologyLoader

EX = Namespace("http://example.org/")


def _write_tiny_owl(tmp_path):
    """Create a minimal OWL file with a subclass chain for reasoning tests.

    Asserted: Measles subClassOf InfectiousDisease, InfectiousDisease subClassOf Disease
    Entailed by OWL RL: Measles subClassOf Disease (transitivity of rdfs:subClassOf)
    """
    g = rdflib.Graph()
    g.bind("ex", EX)
    g.add((EX.Disease, RDF.type, OWL.Class))
    g.add((EX.Disease, RDFS.label, rdflib.Literal("disease")))
    g.add((EX.InfectiousDisease, RDF.type, OWL.Class))
    g.add((EX.InfectiousDisease, RDFS.subClassOf, EX.Disease))
    g.add((EX.InfectiousDisease, RDFS.label, rdflib.Literal("infectious disease")))
    g.add((EX.Measles, RDF.type, OWL.Class))
    g.add((EX.Measles, RDFS.subClassOf, EX.InfectiousDisease))
    g.add((EX.Measles, RDFS.label, rdflib.Literal("measles")))
    owl_path = tmp_path / "test.owl"
    g.serialize(destination=str(owl_path), format="xml")
    return str(owl_path)


class TestOntologyLoader:
    # Req: load graph from path using rdflib
    def test_load_graph_from_file(self, tmp_path):
        owl_path = _write_tiny_owl(tmp_path)
        loader = OntologyLoader(owl_path)
        graph = loader.load_graph()
        assert isinstance(graph, rdflib.Graph)
        # Should contain the asserted triples
        assert (EX.Measles, RDFS.subClassOf, EX.InfectiousDisease) in graph

    # Req: apply OWL RL reasoning to expand graph to deductive closure
    def test_reasoning_entails_transitive_subclass(self, tmp_path):
        owl_path = _write_tiny_owl(tmp_path)
        loader = OntologyLoader(owl_path)
        graph = loader.load_graph()
        graph = loader.apply_reasoning(graph)
        # OWL RL should infer Measles subClassOf Disease via transitivity
        assert (EX.Measles, RDFS.subClassOf, EX.Disease) in graph

    # Req: full pipeline returns Ontology with expanded graph and working matcher
    def test_full_pipeline_returns_ontology(self, tmp_path):
        owl_path = _write_tiny_owl(tmp_path)
        loader = OntologyLoader(owl_path)
        ontology = loader.load()
        assert isinstance(ontology, Ontology)
        # Graph should be expanded
        assert (EX.Measles, RDFS.subClassOf, EX.Disease) in ontology.graph
        # Matcher should recognize labels from the expanded graph
        doc = ontology.nlp("measles is an infectious disease")
        matches = ontology.matcher(doc)
        matched_texts = [doc[start:end].text for _, start, end in matches]
        assert "measles" in matched_texts
        assert "infectious disease" in matched_texts

    # Req: preprocessing order is strict — reasoning before vocabulary building
    def test_vocabulary_built_from_expanded_graph(self, tmp_path):
        owl_path = _write_tiny_owl(tmp_path)
        loader = OntologyLoader(owl_path)
        ontology = loader.load()
        # The entailed triple should be in the graph that the vocabulary was built from
        assert (EX.Measles, RDFS.subClassOf, EX.Disease) in ontology.graph

    # Req: all filesystem paths must be configurable — no hardcoded paths
    def test_accepts_custom_path(self, tmp_path):
        owl_path = _write_tiny_owl(tmp_path)
        loader = OntologyLoader(owl_path)
        assert loader.owl_path == owl_path
