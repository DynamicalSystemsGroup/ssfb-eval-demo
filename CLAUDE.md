# Semantic State Feedback Evaluation Demo

Minimal demonstration of a semantic state feedback evaluation system for LLMs. The system probes an LLM using questions grounded in the APOLLO-SV OWL ontology and evaluates response consistency against ontological facts derived via OWL reasoning.

## Module Layout

```
apollo_eval/
    ontology.py          # Ontology dataclass, ScoreResult dataclass
    ontology_loader.py   # OntologyLoader — loads, reasons over, preprocesses apollo_sv.owl
    vocab.py             # OntologyVocabularyBuilder — builds nlp and matcher from expanded graph
    question.py          # Question base class and concrete question subclasses
    question_loader.py   # 25 concrete questions for measles epidemic scenario
    policy.py            # PolicyEngine — semantic state feedback loop
    model_client.py      # ModelClient ABC + OllamaClient implementation
    evaluation.py        # EvaluationLayer — post-processing, scoring, DataFrame
    utils.py             # lookup() utility
demo.py                  # End-to-end orchestration script
```

## Environment

- Python 3.12 via uv-managed venv (`.venv/`)
- Ollama running locally at `localhost:11434` with `qwen2.5:7b`
- spaCy model: `en_core_web_md` (300D word vectors for similarity matching)
- Similarity threshold: configurable via `Ontology.similarity_threshold` (1.0 = exact only, 0.65 recommended for fuzzy)

## Commands

- Run tests: `.venv/bin/pytest`
- Run demo: `.venv/bin/python demo.py --runs 5`
- Calibrate similarity threshold: `.venv/bin/python calibrate_threshold.py --threshold 0.65`
- Install deps: `uv pip install -r requirements.txt`
- Install spaCy model: `.venv/bin/python -m spacy download en_core_web_md`

## Conventions

- Test-driven development: tests before implementation
- Scientific Python only: rdflib, owlrl, spacy, pyshacl, pandas, pytest
- All filesystem paths and API URLs must be configurable — no hardcoded paths
- Each test includes an inline comment citing the requirement it tests
