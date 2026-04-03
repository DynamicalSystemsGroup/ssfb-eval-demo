# Semantic State Feedback Evaluation Demo

Minimal demonstration of a semantic state feedback evaluation system for LLMs. The system probes an LLM using questions grounded in the APOLLO-SV OWL ontology and evaluates response consistency against ontological facts derived via OWL reasoning.

## Module Layout

```
apollo_eval/
    ontology.py          # Ontology dataclass, ScoreResult dataclass
    ontology_loader.py   # OntologyLoader — loads, reasons over, preprocesses apollo_sv.owl
    vocab.py             # OntologyVocabularyBuilder — builds nlp and matcher from expanded graph
    question.py          # Question base class and concrete question subclasses
    policy.py            # PolicyEngine — semantic state feedback loop
    model_client.py      # ModelClient ABC + OllamaClient implementation
    evaluation.py        # EvaluationLayer — post-processing, scoring, DataFrame
    utils.py             # lookup() utility
demo.py                  # End-to-end orchestration script
```

## Environment

- Python 3.12 via uv-managed venv (`.venv/`)
- Ollama running locally at `localhost:11434` with `qwen2.5:7b`
- spaCy model: `en_core_web_sm`

## Commands

- Run tests: `.venv/bin/pytest`
- Run demo: `.venv/bin/python demo.py --runs 5`
- Install deps: `uv pip install -r requirements.txt`
- Install spaCy model: `.venv/bin/python -m spacy download en_core_web_sm`

## Conventions

- Test-driven development: tests before implementation
- Scientific Python only: rdflib, owlrl, spacy, pyshacl, pandas, pytest
- All filesystem paths and API URLs must be configurable — no hardcoded paths
- Each test includes an inline comment citing the requirement it tests
