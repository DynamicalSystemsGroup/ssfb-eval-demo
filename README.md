# Semantic State Feedback Evaluation Demo

A minimal demonstration of **semantic state feedback** — a framework for evaluating LLM consistency using ontology-grounded probing. The system treats an LLM as a dynamical system with hidden state, applies a policy parameterized by the [APOLLO-SV](http://purl.obolibrary.org/obo/apollo_sv.owl) OWL ontology, and scores responses for consistency against ontological facts derived via OWL reasoning.

For the theoretical framing, see [`semantic_state_feedback_policy.md`](semantic_state_feedback_policy.md).

## How It Works

1. **Load and reason** — The APOLLO-SV ontology is loaded and expanded to its deductive closure via OWL RL reasoning. All entailed triples are materialized before any questions are generated.

2. **Build vocabulary** — Labels and synonyms from the expanded graph are registered as spaCy PhraseMatcher patterns, creating a controlled vocabulary for named entity recognition in LLM responses.

3. **Generate questions** — A fixed question bank is constructed from one ontology scenario. Each question is designed so that a correct response contains parseable ontology-grounded entities.

4. **Run trajectories** — A policy samples questions from a pool without replacement, sends each as a prompt to a local LLM (via Ollama), and records the full input-output trajectory. Multiple independent runs are executed, each with a fresh session and seeded randomness.

5. **Score and evaluate** — Each response is grounded against the ontology vocabulary (spaCy extraction) and checked for consistency (SPARQL ASK or pyshacl validation). Results are aggregated into a pandas DataFrame supporting analysis by question, run, and position.

## Prerequisites

- Python 3.12+
- [Ollama](https://ollama.com) running locally with a Qwen model pulled:

  ```bash
  ollama pull qwen2.5:7b
  ```

## Installation

```bash
# Clone the repository
git clone https://github.com/<your-org>/ssfb-eval-demo.git
cd ssfb-eval-demo

# Create and activate virtual environment (using uv)
uv venv .venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

## Usage

```bash
# Run the full evaluation (5 trajectory runs by default)
python demo.py

# Customize the run
python demo.py --runs 10 --output-dir ./my_trajectories --seed 42
```

### CLI Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--runs` | `5` | Number of independent trajectory runs |
| `--output-dir` | `./trajectories` | Directory for trajectory JSON output |
| `--owl-path` | OBO PURL | Path or URL to the OWL ontology file |
| `--scenario-iri` | *(from ontology)* | IRI of the scenario to evaluate |
| `--seed` | `0` | Base random seed (each run uses `seed + run_index`) |

### Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Model name for Ollama |

## Output

Each run produces a trajectory JSON file in the output directory. After all runs complete, the evaluation layer scores every turn and prints:

- **Consistency rate by question** — How consistently the LLM answers each question correctly across runs
- **Consistency rate by position** — Whether consistency degrades as the conversation progresses
- **Parse failure rate by question** — How often responses could not be grounded to ontology terms

Scores are binary per-turn (1.0 = consistent, 0.0 = contradicts ontology). Aggregations across runs produce continuous values in [0, 1] interpretable as empirical consistency rates. Parse failures are tracked separately and excluded from consistency calculations.

## Running Tests

```bash
pytest
```

## Project Structure

```text
apollo_eval/
    ontology.py          # Ontology and ScoreResult dataclasses
    ontology_loader.py   # OWL loading, reasoning, preprocessing
    vocab.py             # Vocabulary extraction and PhraseMatcher construction
    question.py          # Question base class and concrete subclasses
    policy.py            # Semantic state feedback policy engine
    model_client.py      # LLM client abstraction (Ollama implementation)
    evaluation.py        # Post-hoc scoring and DataFrame construction
    utils.py             # Trajectory lookup utility
demo.py                  # End-to-end orchestration
tests/                   # pytest test suite (one file per module)
```
