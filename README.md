# Semantic State Feedback Evaluation Demo

A minimal demonstration of **semantic state feedback** — a framework for evaluating LLM consistency using ontology-grounded probing. The system treats an LLM as a dynamical system with hidden state, applies a policy parameterized by the [APOLLO-SV](http://purl.obolibrary.org/obo/apollo_sv.owl) OWL ontology, and scores responses for consistency against ontological facts derived via OWL reasoning.

For the theoretical framing, see [`docs/semantic_state_feedback_policy.md`](docs/semantic_state_feedback_policy.md). For the structured literature review organized by research cluster, see [`docs/litreview.jsx`](docs/litreview.jsx).

## About This Demo

This repository is a demo, not the main body of the work, which is ongoing. Its results, including the operator comparison in [`comparison_analysis.ipynb`](comparison_analysis.ipynb), are feasibility results and are published unchanged. The ongoing work continues in:

- [`caie-spec`](https://github.com/DynamicalSystemsGroup/caie-spec): Contextual AI Evaluation as an executable specification, developed with Humane Intelligence.
- J. K. Hollek, M. Zargham, M. Kumar, "Ontology-Based Contextual AI Evaluations (OB-CAIE) Methodology," [arXiv:2610.00529](https://arxiv.org/abs/2610.00529) (2026).
- [`ADCS-lifecycle-demo`](https://github.com/DynamicalSystemsGroup/ADCS-lifecycle-demo): accountability and behavioral modeling of automated systems that are not necessarily generative AI. Its example is an aerospace control system, and our broader argument is that the same paradigm applies to AI systems. It is a controls setting, the home of methods such as system identification, which this demo carries over to LLMs.

## How It Works

1. **Load and reason** — The APOLLO-SV ontology is loaded and expanded to its deductive closure via OWL RL reasoning. All entailed triples are materialized before any questions are generated.

2. **Build vocabulary** — Labels and synonyms from the expanded graph are registered as spaCy PhraseMatcher patterns, creating a controlled vocabulary for named entity recognition in LLM responses.

3. **Generate questions** — A fixed question bank is constructed from one ontology scenario. Each question is designed so that a correct response contains parseable ontology-grounded entities.

4. **Run trajectories** — A policy samples questions from a pool without replacement, sends each as a prompt to a local LLM (via Ollama), and records the full input-output trajectory. Multiple independent runs are executed, each with a fresh session and seeded randomness.

5. **Score and evaluate** — Each response is grounded against the ontology vocabulary (spaCy extraction) and checked for consistency (SPARQL ASK or pyshacl validation). Results are aggregated into a pandas DataFrame supporting analysis by question, run, and position.

## Prerequisites

- Python 3.12+
- [Ollama](https://ollama.com) running locally with a model pulled:

  ```bash
  ollama pull llama3.2:1b
  ```

## Installation

```bash
# Clone the repository
git clone https://github.com/DynamicalSystemsGroup/ssfb-eval-demo.git
cd ssfb-eval-demo

# Create the virtual environment and install the locked dependencies,
# including the spaCy model (en_core_web_md, md for word vectors used in similarity matching)
uv sync
source .venv/bin/activate
```

## Usage

```bash
# Run the full evaluation (5 trajectory runs by default)
python demo.py

# Customize the run
python demo.py --runs 10 --output-dir ./my_trajectories --seed 42

# Verbose mode — see each question and response as it happens
python demo.py --runs 1 --verbose

# Use a different model
python demo.py --runs 5 --model qwen2.5:7b

# Summary statistics for a completed experiment
python summary_stats.py trajectories/batch_25
```

### Analysis Notebook

For interactive exploration with visualizations, use the Jupyter notebook:

```bash
jupyter notebook analysis.ipynb
```

The notebook runs an experiment end-to-end (load ontology, run trajectories, score, visualize). Edit the configuration cell at the top to set `N_RUNS`, `BASE_SEED`, `MODEL`, and `SIMILARITY_THRESHOLD`. Visualizations include:

- Consistency rate by question (colored by type: CM/PR/DJ)
- Consistency rate by question type (with parse failure comparison)
- Position effect (does consistency degrade over the conversation?)
- Parse failure rate by question
- Similarity fallback rate (when fuzzy matching is enabled)
- Per-run consistency (variance across seeds)

### Calibrating Similarity Threshold

The extraction pipeline supports fuzzy matching via word vector similarity. Use the calibration script to empirically validate synonym pairs and tune the threshold:

```bash
# Show all built-in synonym pairs with a threshold sweep
python calibrate_threshold.py

# Show accept/reject decisions at a specific threshold
python calibrate_threshold.py --threshold 0.65

# Test custom synonym pairs
python calibrate_threshold.py --pairs "epidemic:outbreak" "vaccine:jab"

# Interactive mode for ad-hoc testing
python calibrate_threshold.py --interactive
```

### CLI Arguments

| Argument | Default | Description |
| --- | --- | --- |
| `--runs` | `5` | Number of independent trajectory runs |
| `--output-dir` | `./trajectories` | Directory for trajectory JSON output |
| `--owl-path` | OBO PURL | Path or URL to the OWL ontology file |
| `--scenario-iri` | *(from ontology)* | IRI of the scenario to evaluate |
| `--seed` | `0` | Base random seed (each run uses `seed + run_index`) |
| `--model` | `llama3.2:1b` | Ollama model name |
| `--similarity-threshold` | `1.0` | Similarity threshold for fuzzy matching (1.0 = exact only) |
| `--verbose` / `-v` | off | Print each question and response during runs |

### Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `OLLAMA_MODEL` | `llama3.2:1b` | Model name for Ollama |

## Output

Each run produces a trajectory JSON file in the output directory. After all runs complete, the evaluation layer scores every turn and prints:

- **Experiment summary** — Overall parse rate, consistency rate, and per-type (CM/PR/DJ) breakdowns
- **Consistency rate by question type** — Class Membership vs Property Restriction vs Disjointness
- **Consistency rate by question** — Per-question consistency with type, parse failure rate, and fuzz rate
- **Consistency rate by position** — Whether consistency degrades as the conversation progresses
- **Consistency rate by run** — Variance across independent seeds

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
    question_loader.py   # 25 concrete questions for measles epidemic scenario
    policy.py            # Semantic state feedback policy engine
    model_client.py      # LLM client abstraction (Ollama implementation)
    evaluation.py        # Post-hoc scoring and DataFrame construction
    utils.py             # Trajectory lookup utility
demo.py                  # End-to-end CLI orchestration
summary_stats.py         # Post-hoc summary statistics for completed experiments
calibrate_threshold.py   # Similarity threshold calibration tool
analysis.ipynb           # Jupyter notebook — run experiment + visualize results
trajectories/            # Trajectory JSON output (one dir per experiment batch)
docs/                    # Design documents and future considerations
    litreview.jsx        # Interactive literature review (React component)
tests/                   # pytest test suite (one file per module)
```

## Acknowledgments

- **Jamsheed Shorish** (Dynamical Systems Group), on the theoretical model side: the semantic state feedback formalism in [`docs/semantic_state_feedback_policy.md`](docs/semantic_state_feedback_policy.md).
- **Julie Hollek** (Humane Intelligence), on the practical example side: the evaluation demo of probing an LLM and scoring its responses.

Related work with Humane Intelligence: the OB-CAIE paper ([arXiv:2610.00529](https://arxiv.org/abs/2610.00529)) and [`caie-spec`](https://github.com/DynamicalSystemsGroup/caie-spec).

## License

Licensed under the [Apache License 2.0](LICENSE). Copyright 2026 Dynamical Systems Group.
