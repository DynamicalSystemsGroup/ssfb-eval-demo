from abc import ABC, abstractmethod

from apollo_eval.ontology import Ontology, ScoreResult


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
