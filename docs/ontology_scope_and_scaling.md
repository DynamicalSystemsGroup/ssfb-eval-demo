# Ontology Scope and Scaling: From Demo to Framework

## What We Built

The SSFB eval demo implements a single evaluation pipeline: load a full OWL ontology (APOLLO-SV), apply OWL RL reasoning to compute the deductive closure, extract a vocabulary of all labels, and evaluate LLM responses against 25 questions grounded in one measles epidemic scenario.

The pipeline is linear and monolithic:

```
Full OWL file → OWL RL closure → Full vocabulary → PhraseMatcher → Score
```

Every run loads the entire ontology, reasons over all of it, and builds a matcher against all 2,365 extracted labels — regardless of what the questions actually require.

## What We Learned

### Scale mismatch between ontology and evaluation scope

APOLLO-SV contains ~27,000 asserted triples. After OWL RL reasoning, this expands to ~97,000 triples. The vocabulary builder extracts 2,365 unique labels. But our 25-question measles scenario references only ~30 classes and ~6 properties. The evaluation uses roughly 1% of the ontology's conceptual surface area while paying 100% of the load and reasoning cost.

### Vocabulary size affects scoring behavior

The PhraseMatcher and similarity fallback operate over the full 2,365-label vocabulary. When an LLM response mentions an ontology term that is real but irrelevant to the question being scored, it can still match — creating noise in the extraction step. A response about vaccination that happens to mention "geographic region" (a valid APOLLO-SV term) will extract that term even though it has no bearing on the question's expected answer. With exact matching (threshold=1.0) this is mostly harmless noise, but under fuzzy matching (threshold < 1.0) it increases false positive extraction rates because more candidate terms are within similarity range.

### Reasoning cost dominates load time

OWL RL closure is the most expensive step in the pipeline. It scales super-linearly with triple count. For APOLLO-SV this takes several seconds; for larger or more axiomatically rich ontologies (e.g., SNOMED-CT fragments, Gene Ontology) it could take minutes. This cost is paid identically whether we need 30 classes or 3,000.

### Ontology scope is an evaluation design parameter

The choice of what is "in scope" for an evaluation is not just a performance optimization — it is a design decision that affects what the evaluation measures. A question about whether a pathogen is a material entity tests the LLM's consistency against BFO upper-level distinctions. The same question scored against a narrower ontology that excludes BFO would not be evaluable. Conversely, including all of BFO in the vocabulary means the scorer must distinguish between hundreds of upper-level terms that the LLM may use interchangeably.

This means ontology scope is a **sensitivity parameter** of the evaluation: narrow scope produces targeted, high-signal evaluations; broad scope tests whether the model maintains consistency across a larger conceptual space but introduces more parse ambiguity.

### Reproducibility requires explicit scope declarations

When we record that a trajectory was scored against "APOLLO-SV," that is insufficient for reproducibility. The same ontology version with different reasoning profiles (OWL RL vs. OWL DL vs. no reasoning) produces different entailments. A subgraph extraction produces a different evaluation surface than the full graph. Future experiments need to record not just the ontology source but the exact scope configuration: which classes were included, what reasoning was applied, and what matching strategy was used.

The metadata fields we added to trajectory JSON (`ontology_source`, `similarity_threshold`) are a start, but they do not capture scope boundaries.

## Framework Design Considerations

### 1. Subgraph extraction as a first-class operation

The framework should support defining an **evaluation scope** — a set of seed classes and properties — and extracting a minimal subgraph that is sufficient for evaluation. This extracted subgraph, not the full ontology, becomes the input to reasoning and vocabulary building.

Extraction strategies, in order of complexity:

- **Signature-based SPARQL CONSTRUCT**: Given a set of class IRIs, extract their `rdfs:subClassOf` chains, `owl:disjointWith` axioms, property domains/ranges, and annotation labels. Simple, transparent, and easy to audit. Limited to patterns you anticipate.

- **Locality-based module extraction**: OWL module extraction (BOT/TOP/STAR) computes the minimal subset of axioms that preserves all entailments for a given signature. Formally sound — the module is a conservative extension of the full ontology for those terms. Requires OWL API tooling (Java-based `owltools` or a Python wrapper).

- **Transitive closure walk**: Starting from seed IRIs, walk `rdfs:subClassOf`, `owl:equivalentClass`, `rdfs:subPropertyOf`, and selected object property chains up to a configurable depth. More flexible than SPARQL CONSTRUCT, less formal than module extraction. Good middle ground.

- **Manual curation**: For high-stakes evaluations, a domain expert defines the subgraph explicitly. Most controlled, least scalable.

The framework should support all four, selectable per evaluation configuration. The extracted subgraph should be serializable and versionable independently of the source ontology.

### 2. Pre-computed reasoning cache

For a given (ontology version, extraction scope, reasoning profile) triple, the deductive closure is deterministic. The framework should:

- Compute the closure once and serialize it (e.g., as N-Triples or a binary format like HDT)
- Store it alongside the evaluation configuration with a content hash
- Load it directly on subsequent runs, skipping both extraction and reasoning
- Invalidate the cache when any input changes

This converts the most expensive step from a per-run cost to a one-time cost. It also makes the exact set of triples used in evaluation inspectable and diffable.

### 3. Scoped vocabulary building

The vocabulary builder should accept a scope parameter that controls which labels are included in the PhraseMatcher:

- **Full vocabulary**: All labels from the (possibly extracted) subgraph. Current behavior.
- **Question-aligned vocabulary**: Only labels for classes, properties, and individuals referenced by the question bank. Tightest possible scope — minimizes false positive extraction.
- **Depth-bounded vocabulary**: Labels for the seed classes plus N levels of the class hierarchy. Balances coverage with noise.

The matching strategy (exact vs. fuzzy, threshold value) should be configurable per question type or even per question, not just globally. Class membership questions that check for a specific type label may need exact matching, while property restriction questions that look for relationship descriptions in free text may benefit from fuzzy matching.

### 4. Evaluation scope as a versioned configuration object

An evaluation configuration should be a declared, versioned object that fully specifies:

```yaml
ontology:
  source: "http://purl.obolibrary.org/obo/apollo_sv.owl"
  version: "2024-01-15"              # or commit hash
  extraction:
    method: "transitive_closure"     # or "sparql", "locality_module", "manual"
    seed_classes: [...]
    seed_properties: [...]
    depth: 3
  reasoning:
    profile: "owl_rl"
  cache_hash: "sha256:abc123..."

vocabulary:
  scope: "question_aligned"          # or "full", "depth_bounded"
  similarity_threshold: 0.65
  per_type_overrides:
    DJ: { similarity_threshold: 1.0 }

scenario:
  iri: "http://example.org/scenario/measles_epidemic/"
  instance_definitions: "question_loader.py"  # or a separate RDF file
```

This configuration, combined with the question bank, fully determines the evaluation surface. Two experiments with the same configuration and different models produce comparable results. Two experiments with different configurations produce results that are explicitly not directly comparable — the framework should flag this.

### 5. Multi-ontology evaluation

The demo uses a single ontology. Real evaluations will span multiple ontologies with different scopes:

- A **domain ontology** (APOLLO-SV, DO, CHEBI) provides the subject matter
- An **upper ontology** (BFO, SUMO) provides foundational distinctions
- A **scenario ontology** or instance data provides the grounding

These may overlap (APOLLO-SV imports BFO), conflict (different ontologies model "disease" differently), or complement each other. The framework needs to handle:

- **Ontology composition**: Merging graphs from multiple sources before reasoning, with conflict detection
- **Scope per ontology**: Including all of BFO but only a module of APOLLO-SV
- **Cross-ontology questions**: "Is a pathogen (APOLLO-SV) a material entity (BFO)?" requires both ontologies in scope
- **Namespace management**: Avoiding IRI collisions and tracking provenance of entailments

### 6. Sensitivity analysis as a framework feature

Since ontology scope affects evaluation outcomes, the framework should support systematic sensitivity analysis:

- Run the same question bank against progressively wider or narrower scopes
- Compare consistency rates, parse failure rates, and fuzz rates across scope configurations
- Identify which questions are scope-sensitive (their scores change with scope) vs. scope-stable
- Report scope sensitivity as a property of both questions and models

This turns the "how much ontology do we need?" question from a one-time design decision into an empirical measurement.

## Summary

The demo validated the core SSFB evaluation loop: ontology-grounded questions, LLM probing, deterministic scoring. What it exposed is that the relationship between ontology scope and evaluation quality is itself a design surface that the framework must make explicit, configurable, and measurable. The four strategies — subgraph extraction, pre-computed caching, scoped vocabulary, and per-question matching — are not alternatives but layers that address different concerns: correctness, performance, precision, and flexibility.
