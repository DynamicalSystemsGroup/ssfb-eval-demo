# Claude Code Prompt — Semantic State Feedback Evaluation Demo

You are helping me build a minimal demonstration of a **semantic state feedback evaluation system** for LLMs. The system probes an LLM using questions grounded in the APOLLO-SV OWL ontology and evaluates the consistency of its responses against ontological facts derived via OWL reasoning. Read all requirements carefully before writing any code.

---

## Conceptual Framing

The system implements a **semantic state feedback policy** $\pi_\omega$ where:

- $\omega$ is the APOLLO-SV ontology, loaded once, expanded to its deductive closure via OWL RL reasoning, and shared as an `Ontology` object
- Memory $m_t \in M$ is a **pool of unasked questions** — a set of `Question` instances
- The memory operator $\mathcal{M}(u_t, y_t, m_t) = m_t \setminus \{q_t\}$ removes the asked question from the pool
- The policy $\pi_\omega(m_t)$ samples one question from the pool without replacement
- Exit criteria: $m_t = \emptyset$ — the pool is exhausted
- History $h_t$ is maintained separately by the logging layer and grows monotonically — it is the full realization and the primary object of evaluation. Memory and history are distinct: memory shrinks, history grows.

---

## Scoring Pipeline

Each `(question, response)` pair is evaluated for **consistency with ontological facts** entailed by the expanded graph. The pipeline has four steps:

```
1. Reason     — owlrl expands the graph to its deductive closure at load time.
                All entailed triples are materialized into the graph before any
                questions are built. Questions are written against the closed world.

2. Design     — questions are crafted so that a correct response will naturally
                contain entities and relations from the ontology's controlled
                vocabulary. We control the question design, so we can make
                correct responses parseable by construction.

3. Extract    — spaCy + PhraseMatcher maps response text to valid RDF terms
                from the controlled vocabulary. spaCy's role is named entity
                recognition against the ontology vocabulary — a grounding step,
                not a similarity step. If no triple can be extracted, this is
                recorded as a parse failure (not a consistency failure).

4. Check      — extracted triple(s) are checked for consistency against the
                expanded graph via SPARQL ASK query and/or pyshacl validation
                against a SHACL shape derived from the OWL restriction that
                grounds this question.
```

### Scoring

Per-record score is **binary**:
- `1.0` — extracted triple(s) are consistent with the expanded graph
- `0.0` — extracted triple(s) contradict an entailed fact or violate a SHACL constraint
- Parse failures are recorded separately as `parse_success: bool` — they are not scored as `0.0`

Per-record scores are binary but aggregations across `run_id`, `question_id`, and `position_index` produce continuous values in `[0, 1]` that are interpretable as empirical consistency rates. This is the primary analysis quantity.

### Question Design Requirements

Each concrete `Question` subclass must:
- Be designed so that a correct response will contain parseable ontology-grounded entities
- Document in a comment which OWL axiom or restriction in the expanded graph it is testing
- Target one of these three response patterns:
  - `[entity] is a [class]` — tests class membership entailment
  - `[entity] has [property] [value]` — tests property restriction entailment
  - `[entity] cannot [property] [value]` — tests disjointness or negative constraint

At least one question must exercise pyshacl validation. At least one must exercise SPARQL ASK only. Both paths must be clearly identifiable in the code.

---

## Core Data Structures

### `Ontology` dataclass

```python
@dataclass
class Ontology:
    graph: rdflib.Graph        # OWL graph expanded to deductive closure via owlrl
    nlp: spacy.Language        # spaCy model with vocabulary pre-populated from expanded graph
    matcher: PhraseMatcher     # ontology label patterns for span recognition in responses
```

- `Ontology` is the single coherent container for all ontology-derived resources
- `graph`, `nlp`, and `matcher` must always be consistent — all three are derived from the same expanded graph and constructed together
- Constructed once by `OntologyLoader` and passed as a dependency to all components
- Extensibility: future additions (SHACL shapes graph, SPARQL endpoint) belong here

### `Question` class

```python
class Question:
    ontology: Ontology   # class-level attribute — single shared Ontology, set once

    question_id: str     # stable UUID, generated once and hardcoded per question
    prompt: str          # text sent to the LLM — designed to elicit parseable response

    def score(self, response: str) -> ScoreResult: ...
```

### `ScoreResult` dataclass

```python
@dataclass
class ScoreResult:
    question_id: str
    parse_success: bool      # whether a triple could be extracted from the response
    score: float             # 1.0 (consistent) or 0.0 (contradicts ontology)
                             # only meaningful when parse_success is True
```

- `ontology` is a **class-level** attribute set once via `Question.ontology = ontology`
- Each concrete `Question` subclass implements `score()` using the four-step pipeline above
- `score()` always returns a `ScoreResult` — parse failures never raise exceptions

---

## Architecture

### Module layout (propose this first, before any implementation)

```
apollo_eval/
    __init__.py
    ontology.py          # Ontology dataclass, ScoreResult dataclass
    ontology_loader.py   # OntologyLoader — loads, reasons over, and preprocesses apollo_sv.owl
    vocab.py             # OntologyVocabularyBuilder — builds nlp and matcher from expanded graph
    question.py          # Question base class and concrete question subclasses
    policy.py            # PolicyEngine
    model_client.py      # ModelClient ABC + OllamaClient implementation
    evaluation.py        # EvaluationLayer — post-processing, scoring, DataFrame
    utils.py             # lookup() utility
demo.py
tests/
    test_ontology_loader.py
    test_vocab.py
    test_question.py
    test_policy.py
    test_model_client.py
    test_evaluation.py
    test_utils.py
requirements.txt
README.md
```

---

### `Ontology` and `ScoreResult` (`ontology.py`)

- Pure data containers — no logic
- Import target for all other modules

---

### `OntologyVocabularyBuilder` (`vocab.py`)

- Accepts an expanded `rdflib.Graph` (post-owlrl reasoning)
- Extracts all `rdfs:label`, `skos:prefLabel`, `skos:altLabel`, and `oboInOwl:hasExactSynonym` annotation values
- Adds each label to the spaCy vocab using `nlp.vocab.strings.add()`
- For multi-word labels, adds them as `PhraseMatcher` patterns for span recognition
- Returns a fully constructed `Ontology` instance
- Must select an appropriate base spaCy model (justify the choice in a comment)

---

### `OntologyLoader` (`ontology_loader.py`)

Preprocessing order is strict and must be followed exactly:

```
1. graph    = load_graph(owl_path)                             # rdflib — asserted triples
2. graph    = apply_reasoning(graph)                           # owlrl — deductive closure
3. ontology = OntologyVocabularyBuilder(graph).build()         # Ontology from expanded graph
4. Question.ontology = ontology                                # set class-level attribute
5. Q        = generate_question_bank(ontology, scenario_iri)   # questions over closed world
```

- Load `apollo_sv.owl` from OBO PURL: `http://purl.obolibrary.org/obo/apollo_sv.owl` using `rdflib`
- Apply OWL RL reasoning using `owlrl` to expand the graph to its deductive closure
- Extract one scenario: one `infectious disease scenario` subclass with associated `population`, `control measure`, and `transmission parameter` instances or restrictions
- Generate a fixed question bank $Q$ — a set of `Question` instances — from the scenario
- The question bank is fixed for all runs of a given scenario

---

### `PolicyEngine` (`policy.py`)

- Implements $\pi_\omega(m_t) \to u_{t+1}$ as a deterministic Python function
- `memory` $m_t$ is a set of `Question` instances — the unasked question pool
- At each turn: sample one question from pool using seeded `random` (seed recorded in run metadata), remove it from pool via $\mathcal{M}$, return the question and its prompt as $u_{t+1}$
- Exit predicate signature: `exit_criteria(memory: set[Question]) -> bool`; default returns `True` when pool is empty
- Exit predicate is pluggable — accept any callable with that signature
- History accumulator is separate from memory: `h.append((u_t, y_t))` after each turn

---

### `ModelClient` (`model_client.py`)

- Abstract base class with one abstract method: `complete(history: list[tuple[str, str]], prompt: str) -> str`
- Each trajectory is an **independent session** — client instantiated fresh per run, no shared state between runs
- `OllamaClient(ModelClient)` — targets local Ollama instance running Qwen
- Ollama API base URL and model name configurable via environment variables `OLLAMA_BASE_URL` and `OLLAMA_MODEL`

---

### `EvaluationLayer` (`evaluation.py`)

- Post-processing only — runs after all trajectories are collected, entirely separate from the control loop
- Loads trajectory JSON files from a configurable directory
- Reconstructs `Question` instances by `question_id` to call `question.score(y_t)` for each turn
- Produces a pandas DataFrame with schema:

```
question_id (str), run_id (str), position_index (int),
parse_success (bool), score (float)
```

- `score` is `NaN` when `parse_success` is `False` — parse failures must not contaminate consistency rate aggregations
- DataFrame must support segmentation by `question_id`, `run_id`, and `position_index`
- Aggregations across any dimension produce empirical consistency rates in `[0, 1]`

---

### `utils.py`

- `lookup(run_id: str, position_index: int, trajectory_dir: str) -> dict` — loads the correct trajectory JSON and returns the full turn record at the given `position_index`

---

## Trajectory JSON Schema

One file per run, filename `<run_id>.json`:

```json
{
  "run_id": "<uuid>",
  "seed": "<int>",
  "scenario_iri": "<iri>",
  "turns": [
    {
      "position_index": "<int>",
      "question_id": "<uuid>",
      "u": "<prompt text>",
      "y": "<response text>",
      "parse_success": "<bool>",
      "score": "<float | null>"
    }
  ]
}
```

- `score` is `null` in JSON when `parse_success` is `false`

---

## Demo Script (`demo.py`)

- Loads ontology, applies reasoning, builds vocabulary, builds question bank — in strict preprocessing order
- Runs `N` independent trajectory runs (default `N=5`, configurable via CLI argument)
- Each run: fresh `ModelClient` instance, fresh memory pool copied from question bank, independent seed
- Writes one trajectory JSON per run to a configurable output directory
- After all runs: instantiates `EvaluationLayer`, scores all trajectories, prints the scores DataFrame
- Prints summary statistics:
  - Mean consistency rate by `question_id`
  - Mean consistency rate by `position_index`
  - Parse failure rate by `question_id`

---

## Development Protocol

- **Test-driven development**: write tests before implementation. Each test must include an inline comment citing the requirement it is testing.
- Tests must be runnable with `pytest`
- Use scientific Python only: `rdflib`, `owlrl`, `spacy`, `pyshacl`, `pandas`, `pytest`. No heavyweight ML frameworks.
- All filesystem paths and API URLs must be configurable — no hardcoded paths or URLs.

---

## Deliverables — in this order

1. Proposed module layout with brief description of each module's responsibility
2. Test specifications for all modules — tests written first, no implementation yet
3. **Await my approval before proceeding to implementation**
4. Implementation of all modules
5. `demo.py`
6. `requirements.txt`
7. `README.md` — how to run, what to expect, how to interpret the scores DataFrame and consistency rate aggregations

---

**Do not begin writing tests or implementation until you have shown me the module layout and I have approved it.**
