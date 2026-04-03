import rdflib
import owlrl

from apollo_eval.ontology import Ontology
from apollo_eval.vocab import OntologyVocabularyBuilder

DEFAULT_OWL_URL = "http://purl.obolibrary.org/obo/apollo_sv.owl"


class OntologyLoader:
    """Loads an OWL ontology, applies OWL RL reasoning, and builds an Ontology.

    Preprocessing order is strict:
    1. Load graph from path/URL (rdflib — asserted triples)
    2. Apply OWL RL reasoning (owlrl — deductive closure)
    3. Build Ontology via OntologyVocabularyBuilder (nlp + matcher from expanded graph)
    """

    def __init__(self, owl_path: str = DEFAULT_OWL_URL):
        self.owl_path = owl_path

    def load_graph(self) -> rdflib.Graph:
        """Load the OWL file into an rdflib Graph."""
        graph = rdflib.Graph()
        graph.parse(self.owl_path)
        return graph

    def apply_reasoning(self, graph: rdflib.Graph) -> rdflib.Graph:
        """Expand graph to its deductive closure via OWL RL reasoning."""
        owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)
        return graph

    def load(self) -> Ontology:
        """Full pipeline: load, reason, build vocabulary."""
        graph = self.load_graph()
        graph = self.apply_reasoning(graph)
        return OntologyVocabularyBuilder(graph).build()
