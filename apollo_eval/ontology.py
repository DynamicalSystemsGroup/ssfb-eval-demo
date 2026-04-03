from dataclasses import dataclass

import rdflib
import spacy
from spacy.matcher import PhraseMatcher


@dataclass
class Ontology:
    """Single coherent container for all ontology-derived resources.

    Constructed once by OntologyLoader and passed as a dependency to all components.
    graph, nlp, and matcher must always be consistent — all three are derived from
    the same expanded graph and constructed together.
    """

    graph: rdflib.Graph
    nlp: spacy.Language
    matcher: PhraseMatcher


@dataclass
class ScoreResult:
    """Result of scoring a single (question, response) pair.

    score is 1.0 (consistent) or 0.0 (contradicts ontology) when parse_success
    is True. When parse_success is False, score is not meaningful — the evaluation
    layer converts it to NaN for aggregation.
    """

    question_id: str
    parse_success: bool
    score: float
