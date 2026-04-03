from dataclasses import dataclass, field

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
    vocab_labels: list[str]
    similarity_threshold: float = 1.0  # 1.0 = exact match only, lower = fuzzy

    _vocab_docs: dict | None = field(default=None, repr=False, init=False)

    def get_vocab_docs(self) -> dict:
        """Lazily compute and cache Doc objects for all vocab labels.

        Only called when similarity_threshold < 1.0. Each label is processed
        through the full NLP pipeline once and cached for reuse.
        """
        if self._vocab_docs is None:
            self._vocab_docs = {label: self.nlp(label) for label in self.vocab_labels}
        return self._vocab_docs


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
    fuzz: bool | None = None  # False=exact, True=similarity fallback, None=non-parse
