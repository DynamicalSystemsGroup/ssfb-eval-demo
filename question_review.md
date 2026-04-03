# Question Bank Review — 25 Questions with 5 Test Responses Each

This document lists every question in the evaluation bank, its ontological grounding, the five mocked test responses, and an explanation of why each receives its score.

## Scoring Logic

The scoring pipeline has three possible outcomes per response:

| Outcome | `parse_success` | `score` | Meaning |
| --- | --- | --- | --- |
| **Pass (1.0)** | `True` | `1.0` | Response contains ontology terms AND agrees with the ontological fact |
| **Fail (0.0)** | `True` | `0.0` | Response contains ontology terms BUT contradicts the ontological fact |
| **Non-parse** | `False` | N/A | Response contains no ontology terms — cannot be scored |

## Extraction Pipeline

Term extraction is two-stage:

1. **Exact match (always):** spaCy PhraseMatcher against ontology vocabulary (case-insensitive)
2. **Similarity fallback (only when threshold < 1.0 AND exact match found nothing):** token/span cosine similarity against ontology label vectors using `en_core_web_md` 300D GloVe vectors

The `similarity_threshold` parameter controls the dial:
- **1.0** = exact match only (no fallback)
- **0.65** = recommended fuzzy threshold (validated against empirical synonym pair scores)

**Negation detection** determines response polarity via spaCy dependency parsing (`dep_=="neg"`) and a lexical fallback for tokens like "not", "no", "cannot", "doesn't", etc.

### Validated Synonym Pairs (en_core_web_md)

| Ontology Label | Synonym Used | Cosine Similarity |
| --- | --- | --- |
| epidemic | outbreak | 1.00 |
| vaccination | immunization | 1.00 |
| disease | illness | 1.00 |
| pathogen | microbe | 0.76 |
| pathogenic disposition | virulence | 0.80 |
| drug treatment | pharmaceutical therapy | 0.68 |
| disorder | ailment | 0.65 |
| infection in ecosystem | contagion in environment | 0.71 |

---

## Q1–Q12: Class Membership (SPARQL ASK)

These questions test `entity rdf:type class` — either directly asserted or entailed via `rdfs:subClassOf` transitivity after OWL RL reasoning.

---

### Q1 — Epidemic instance is an epidemic

- **Prompt:** "How would you classify a measles epidemic in epidemiological terms?"
- **OWL axiom:** `SCENARIO.measles_epidemic rdf:type APOLLO_SV:epidemic` (direct assertion)
- **Check method:** SPARQL ASK `{ ?entity a ?class }`

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "A measles epidemic is an epidemic event." | 1.0 | **1.0** | PhraseMatcher extracts "epidemic". No negation. Graph confirms membership. Affirming a true fact. |
| 2 | "A measles epidemic is not an epidemic." | 1.0 | **0.0** | Extracts "epidemic". Negation "not" detected. Negating a true fact. |
| 3 | "A measles outbreak is a widespread event." | 0.65 | **1.0** | "outbreak" matches "epidemic" via similarity (1.00). No negation. Graph confirms. |
| 4 | "A measles outbreak is not a widespread event." | 0.65 | **0.0** | "outbreak" matches "epidemic" (1.00). Negation "not" detected. Negating a true fact. |
| 5 | "The weather forecast calls for rain tomorrow." | 1.0 | **non-parse** | No ontology terms found. Completely unrelated text. |

---

### Q2 — Epidemic is an infection in ecosystem (entailed)

- **Prompt:** "What broader category does an epidemic fall under in terms of ecological processes?"
- **OWL axiom:** `epidemic rdfs:subClassOf infection_in_ecosystem` → entails `measles_epidemic a infection_in_ecosystem`
- **Check method:** SPARQL ASK `{ ?entity a ?class }`

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "An epidemic is a type of infection in ecosystem." | 1.0 | **1.0** | Extracts "epidemic", "infection in ecosystem". No negation. Entailed via subClassOf. |
| 2 | "An epidemic is not an infection in ecosystem." | 1.0 | **0.0** | Same extraction. Negation "not" detected. Contradicts entailed fact. |
| 3 | "An outbreak is a type of contagion in an environment." | 0.65 | **1.0** | "outbreak"→"epidemic" (1.00), "contagion in an environment"→"infection in ecosystem" (0.71). No negation. |
| 4 | "An outbreak is not a contagion in an environment." | 0.65 | **0.0** | Same similarity matches. Negation "not" detected. |
| 5 | "It spreads through communities rapidly." | 1.0 | **non-parse** | No ontology terms. "communities" not in vocabulary. |

---

### Q3 — Vaccination strategy is a vaccination control strategy (direct)

- **Prompt:** "How is a vaccination program categorized as a public health intervention?"
- **OWL axiom:** `SCENARIO.vaccination_strategy rdf:type vaccination_control_strategy` (direct)
- **Check method:** SPARQL ASK

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "It is a vaccination control strategy." | 1.0 | **1.0** | Extracts "vaccination control strategy". No negation. Direct assertion confirmed. |
| 2 | "It is not a vaccination control strategy." | 1.0 | **0.0** | Same extraction. Negation "not" detected. |
| 3 | "It is an immunization control strategy." | 0.65 | **1.0** | "immunization"→"vaccination" (1.00). No negation. Graph confirms. |
| 4 | "It is not an immunization control strategy." | 0.65 | **0.0** | Same similarity match. Negation "not" detected. |
| 5 | "It is a plan for public health." | 1.0 | **non-parse** | No ontology terms. |

---

### Q4 — Vaccination control strategy is individual treatment control strategy (entailed)

- **Prompt:** "What level of intervention does a vaccination control strategy target?"
- **OWL axiom:** `vaccination_control_strategy rdfs:subClassOf individual_treatment_control_strategy`
- **Check method:** SPARQL ASK

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "A vaccination control strategy is an individual treatment control strategy." | 1.0 | **1.0** | Extracts both multi-word labels. No negation. Entailed membership confirmed. |
| 2 | "A vaccination control strategy is not an individual treatment control strategy." | 1.0 | **0.0** | Same extraction. Negation "not" detected. Contradicts entailed fact. |
| 3 | "An immunization control strategy is an individual treatment control strategy." | 0.65 | **1.0** | "immunization"→"vaccination" (1.00). No negation. Entailed. |
| 4 | "An immunization control strategy is not an individual treatment control strategy." | 0.65 | **0.0** | Same similarity match. Negation detected. |
| 5 | "It targets specific patients." | 1.0 | **non-parse** | No ontology terms. |

---

### Q5 — Vaccination control strategy is infectious disease control strategy (entailed chain)

- **Prompt:** "What is the relationship between vaccination strategies and broader disease control frameworks?"
- **OWL axiom:** `vaccination_control_strategy subClassOf individual_treatment_control_strategy subClassOf infectious_disease_control_strategy` (two-hop)
- **Check method:** SPARQL ASK

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "A vaccination control strategy is an infectious disease control strategy." | 1.0 | **1.0** | Both labels extracted. No negation. Two-hop entailment materialized by OWL RL. |
| 2 | "A vaccination control strategy is not an infectious disease control strategy." | 1.0 | **0.0** | Negation detected. Contradicts entailed relationship. |
| 3 | "An immunization strategy is a communicable illness control strategy." | 0.65 | **1.0** | "immunization"→"vaccination" (1.00), "communicable illness"→"infectious disease" (0.84). No negation. |
| 4 | "An immunization strategy is not a communicable illness control strategy." | 0.65 | **0.0** | Same similarity matches. Negation detected. |
| 5 | "It helps prevent spread." | 1.0 | **non-parse** | No ontology terms. |

---

### Q6 — Quarantine control strategy is infectious disease control strategy (entailed)

- **Prompt:** "How does quarantine fit within the hierarchy of disease control approaches?"
- **OWL axiom:** `quarantine_control_strategy rdfs:subClassOf infectious_disease_control_strategy`
- **Check method:** SPARQL ASK

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "A quarantine control strategy is an infectious disease control strategy." | 1.0 | **1.0** | Both labels extracted. No negation. Entailed membership confirmed. |
| 2 | "A quarantine control strategy is not an infectious disease control strategy." | 1.0 | **0.0** | Negation "not" detected. Contradicts entailed subclass relationship. |
| 3 | "Quarantine is a communicable illness control strategy." | 0.65 | **1.0** | "communicable illness"→"infectious disease" (0.84). No negation. |
| 4 | "Quarantine is not a communicable illness control strategy." | 0.65 | **0.0** | Same similarity match. Negation detected. |
| 5 | "It involves isolating people." | 1.0 | **non-parse** | No ontology terms. |

---

### Q7 — Vaccination treatment is a vaccination (direct)

- **Prompt:** "What kind of medical procedure is vaccination?"
- **OWL axiom:** `SCENARIO.vacc_treatment rdf:type vaccination` (direct)
- **Check method:** SPARQL ASK

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "Vaccination is classified as a vaccination procedure." | 1.0 | **1.0** | Extracts "vaccination". No negation. Direct type assertion confirmed. |
| 2 | "Vaccination is not a vaccination in the formal sense." | 1.0 | **0.0** | Extracts "vaccination". Negation "not" detected. Contradicts direct assertion. |
| 3 | "Immunization is classified as a medical procedure." | 0.65 | **1.0** | "immunization"→"vaccination" (1.00). No negation. |
| 4 | "Immunization is not classified as a medical procedure." | 0.65 | **0.0** | Same similarity match. Negation detected. |
| 5 | "It is an injection given to patients." | 1.0 | **non-parse** | No ontology terms. |

---

### Q8 — Vaccination is a treatment (entailed)

- **Prompt:** "How is vaccination categorized in clinical practice?"
- **OWL axiom:** `vaccination rdfs:subClassOf treatment`
- **Check method:** SPARQL ASK

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "Vaccination is a type of treatment." | 1.0 | **1.0** | Extracts "vaccination", "treatment". No negation. Entailed via subClassOf. |
| 2 | "Vaccination is not a treatment." | 1.0 | **0.0** | Negation "not" detected. Contradicts entailed relationship. |
| 3 | "Immunization is a type of treatment." | 0.65 | **1.0** | "immunization"→"vaccination" (1.00). No negation. Entailed. |
| 4 | "Immunization is not a treatment." | 0.65 | **0.0** | Same similarity match. Negation detected. |
| 5 | "It is a preventive measure." | 1.0 | **non-parse** | "preventive measure" not an ontology label. |

---

### Q9 — Drug treatment is a treatment (entailed)

- **Prompt:** "What category does pharmacological intervention fall under in medical ontology?"
- **OWL axiom:** `drug_treatment rdfs:subClassOf treatment`
- **Check method:** SPARQL ASK

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "Drug treatment is a type of treatment." | 1.0 | **1.0** | Extracts "drug treatment", "treatment". No negation. Entailed. |
| 2 | "Drug treatment is not a treatment." | 1.0 | **0.0** | Negation detected. Contradicts entailed fact. |
| 3 | "Pharmaceutical therapy is a type of treatment." | 0.65 | **1.0** | "pharmaceutical therapy"→"drug treatment" (0.68). No negation. |
| 4 | "Pharmaceutical therapy is not a treatment." | 0.65 | **0.0** | Same similarity match. Negation detected. |
| 5 | "Patients take medication regularly." | 1.0 | **non-parse** | No ontology terms. |

---

### Q10 — Pathogen is a pathogen (direct)

- **Prompt:** "What is the role of the measles causative agent in the disease process?"
- **OWL axiom:** `SCENARIO.measles_pathogen rdf:type pathogen` (direct)
- **Check method:** SPARQL ASK

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "The causative agent is classified as a pathogen." | 1.0 | **1.0** | Extracts "pathogen". No negation. Direct assertion confirmed. |
| 2 | "The agent is not a pathogen." | 1.0 | **0.0** | Extracts "pathogen". Negation "not" detected. |
| 3 | "The causative agent is a microbe." | 0.65 | **1.0** | "microbe"→"pathogen" (0.76). No negation. |
| 4 | "The causative agent is not a microbe." | 0.65 | **0.0** | Same similarity match. Negation detected. |
| 5 | "It causes illness in people." | 1.0 | **non-parse** | No ontology terms. |

---

### Q11 — Pathogen is an organism (entailed)

- **Prompt:** "What is the biological classification of a pathogen?"
- **OWL axiom:** `pathogen rdfs:subClassOf organism`
- **Check method:** SPARQL ASK

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "A pathogen is a type of organism." | 1.0 | **1.0** | Extracts "pathogen", "organism". No negation. Entailed via subClassOf. |
| 2 | "A pathogen is not an organism." | 1.0 | **0.0** | Negation detected. Contradicts entailed fact. |
| 3 | "A microbe is a type of organism." | 0.65 | **1.0** | "microbe"→"pathogen" (0.76). No negation. Entailed. |
| 4 | "A microbe is not an organism." | 0.65 | **0.0** | Same similarity match. Negation detected. |
| 5 | "It is a living thing." | 1.0 | **non-parse** | "living thing" not an ontology label. |

---

### Q12 — Population infection survey is a population survey (entailed)

- **Prompt:** "How would you categorize a population infection survey within epidemiological data collection?"
- **OWL axiom:** `population_infection_survey rdfs:subClassOf population_survey`
- **Check method:** SPARQL ASK

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "A population infection survey is a type of population survey." | 1.0 | **1.0** | Extracts both multi-word labels. No negation. Entailed. |
| 2 | "A population infection survey is not a population survey." | 1.0 | **0.0** | Negation detected. Contradicts entailed subclass relationship. |
| 3 | "A population infection survey is a population survey by definition." | 0.65 | **1.0** | Exact match still works at lower threshold. No negation. |
| 4 | "A population infection survey is not a population survey at all." | 0.65 | **0.0** | Exact match. Negation detected. |
| 5 | "It collects data on illness rates." | 1.0 | **non-parse** | No ontology terms. |

---

## Q13–Q20: Property Restriction (pyshacl)

These questions test `entity property value` — verified by constructing a SHACL NodeShape requiring the entity to have the expected property-value pair, then running pyshacl validation against the data graph.

---

### Q13 — Scenario is about ecosystem

- **Prompt:** "What is the primary subject matter of an infectious disease scenario?"
- **OWL restriction:** `infectious_disease_scenario some is_about ecosystem`
- **Scenario assertion:** `SCENARIO.measles_scenario is_about SCENARIO.target_ecosystem`
- **Check method:** pyshacl — NodeShape requiring `measles_scenario → is_about → target_ecosystem`

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "An infectious disease scenario is about an ecosystem." | 1.0 | **1.0** | Extracts "infectious disease scenario", "ecosystem". No negation. pyshacl confirms. |
| 2 | "An infectious disease scenario is not about an ecosystem." | 1.0 | **0.0** | Same extraction. Negation "not" detected. Triple exists but response denies it. |
| 3 | "A communicable illness scenario concerns an ecosystem." | 0.65 | **1.0** | "communicable illness"→"infectious disease" (0.84). No negation. pyshacl confirms. |
| 4 | "A communicable illness scenario does not concern an ecosystem." | 0.65 | **0.0** | Same similarity match. Negation detected. |
| 5 | "It models environmental conditions broadly." | 1.0 | **non-parse** | No ontology terms. |

---

### Q14 — Infection acquisition causally upstream of infection

- **Prompt:** "What is the causal relationship between acquiring a pathogen and the resulting disease process?"
- **OWL restriction:** `infection_acquisition some causally_upstream_of infection`
- **Scenario assertion:** `SCENARIO.measles_acquisition causally_upstream_of SCENARIO.measles_infection`
- **Check method:** pyshacl

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "Infection acquisition leads to infection." | 1.0 | **1.0** | Extracts "infection acquisition", "infection". No negation. pyshacl confirms. |
| 2 | "Infection acquisition does not lead to infection." | 1.0 | **0.0** | Negation "not" detected. Triple exists but response denies it. |
| 3 | "Infection acquisition causes infection to develop." | 0.65 | **1.0** | Exact match still works (these terms lack good synonyms). No negation. |
| 4 | "Infection acquisition does not cause infection to develop." | 0.65 | **0.0** | Exact match. Negation detected. |
| 5 | "Exposure to a germ causes illness." | 1.0 | **non-parse** | "exposure", "germ", "illness" not in vocabulary. |

---

### Q15 — Infection immediately preceded by infection acquisition

- **Prompt:** "What process occurs immediately before an infection begins?"
- **OWL restriction:** `infection some immediately_preceded_by infection_acquisition`
- **Scenario assertion:** `SCENARIO.measles_infection immediately_preceded_by SCENARIO.measles_acquisition`
- **Check method:** pyshacl

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "Infection is preceded by infection acquisition." | 1.0 | **1.0** | Extracts "infection", "infection acquisition". No negation. pyshacl confirms. |
| 2 | "Infection is not preceded by infection acquisition." | 1.0 | **0.0** | Negation detected. Contradicts asserted relationship. |
| 3 | "Infection follows infection acquisition directly." | 0.65 | **1.0** | Exact match (domain-specific terms). No negation. |
| 4 | "Infection does not follow infection acquisition." | 0.65 | **0.0** | Exact match. Negation detected. |
| 5 | "One stage follows another in sequence." | 1.0 | **non-parse** | No ontology terms. |

---

### Q16 — Pathogen bearer of pathogenic disposition

- **Prompt:** "What inherent properties does a pathogen possess that enable it to cause disease?"
- **OWL restriction:** `pathogen some bearer_of infectiousness`
- **Scenario assertion:** `SCENARIO.measles_pathogen bearer_of SCENARIO.pathogenic_disposition`
- **Check method:** pyshacl

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "A pathogen bears a pathogenic disposition." | 1.0 | **1.0** | Extracts "pathogen", "pathogenic disposition". No negation. pyshacl confirms. |
| 2 | "A pathogen does not bear a pathogenic disposition." | 1.0 | **0.0** | Negation "not" detected. Triple exists but response denies it. |
| 3 | "A microbe possesses virulence." | 0.65 | **1.0** | "microbe"→"pathogen" (0.76), "virulence"→"pathogenic disposition" (0.80). No negation. |
| 4 | "A microbe does not possess virulence." | 0.65 | **0.0** | Same similarity matches. Negation detected. |
| 5 | "It has the ability to cause harm." | 1.0 | **non-parse** | No ontology terms ("harm", "ability" not in vocabulary). |

---

### Q17 — Vaccination has participant host

- **Prompt:** "Who are the participants in a vaccination procedure?"
- **OWL restriction:** `vaccination some has_participant` (host)
- **Scenario assertion:** `SCENARIO.vacc_treatment has_participant SCENARIO.human_host`
- **Check method:** pyshacl

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "Vaccination has a host as participant." | 1.0 | **1.0** | Extracts "vaccination", "host". No negation. pyshacl confirms. |
| 2 | "Vaccination does not have a host as participant." | 1.0 | **0.0** | Negation "not" detected. Triple exists but response denies it. |
| 3 | "Immunization involves a host as participant." | 0.65 | **1.0** | "immunization"→"vaccination" (1.00). No negation. pyshacl confirms. |
| 4 | "Immunization does not involve a host as participant." | 0.65 | **0.0** | Same similarity match. Negation detected. |
| 5 | "A patient receives the injection." | 1.0 | **non-parse** | No ontology terms. |

---

### Q18 — Epidemic occurs in ecosystem

- **Prompt:** "Where does an epidemic take place in ecological terms?"
- **Scenario assertion:** `SCENARIO.measles_epidemic occurs_in SCENARIO.target_ecosystem`
- **Check method:** pyshacl

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "An epidemic occurs in an ecosystem." | 1.0 | **1.0** | Extracts "epidemic", "ecosystem". No negation. pyshacl confirms. |
| 2 | "An epidemic does not occur in an ecosystem." | 1.0 | **0.0** | Negation detected. Contradicts asserted triple. |
| 3 | "An outbreak occurs in an ecosystem." | 0.65 | **1.0** | "outbreak"→"epidemic" (1.00). No negation. |
| 4 | "An outbreak does not occur in an ecosystem." | 0.65 | **0.0** | Same similarity match. Negation detected. |
| 5 | "It happens in a community setting." | 1.0 | **non-parse** | "community" not in vocabulary. |

---

### Q19 — Infection acquisition has participant pathogen

- **Prompt:** "What biological entities participate in the process of infection acquisition?"
- **Scenario assertion:** `SCENARIO.measles_acquisition has_participant SCENARIO.measles_pathogen`
- **Check method:** pyshacl

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "Infection acquisition involves a pathogen." | 1.0 | **1.0** | Extracts "infection acquisition", "pathogen". No negation. pyshacl confirms. |
| 2 | "Infection acquisition does not involve a pathogen." | 1.0 | **0.0** | Negation detected. Triple exists but response denies it. |
| 3 | "Infection acquisition involves a microbe." | 0.65 | **1.0** | "microbe"→"pathogen" (0.76). No negation. |
| 4 | "Infection acquisition does not involve a microbe." | 0.65 | **0.0** | Same similarity match. Negation detected. |
| 5 | "The germ enters the body." | 1.0 | **non-parse** | No ontology terms. |

---

### Q20 — Vaccination does NOT have pathogen as participant (negative test)

- **Prompt:** "Does a vaccination procedure directly interact with the disease-causing agent?"
- **Graph fact:** The triple `SCENARIO.vacc_treatment has_participant SCENARIO.measles_pathogen` is **absent** from the graph. pyshacl validation **fails** (non-conforming).
- **Check method:** pyshacl — this is a negative test: the SHACL shape expects a triple that doesn't exist.

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "Vaccination does not involve a pathogen as participant." | 1.0 | **1.0** | Extracts "vaccination", "pathogen". Negation "not" detected. pyshacl says triple is absent (conforms=False). Negating an absent property → consistent. |
| 2 | "Vaccination involves a pathogen as participant." | 1.0 | **0.0** | Same extraction. No negation. Affirming an absent property → inconsistent. |
| 3 | "Immunization does not interact with a microbe directly." | 0.65 | **1.0** | "immunization"→"vaccination" (1.00), "microbe"→"pathogen" (0.76). Negation detected. Correctly denying absent triple. |
| 4 | "Immunization interacts with a microbe directly." | 0.65 | **0.0** | Same similarity matches. No negation. Affirming absent property. |
| 5 | "The procedure targets the immune system." | 1.0 | **non-parse** | No ontology terms. |

---

## Q21–Q25: Disjointness (SPARQL ASK)

These questions test `owl:disjointWith` constraints. The check verifies that the entity is NOT a member of the disjoint class. Disjointness questions expect **negation** for a consistent response — "No, X cannot be Y" is the correct answer when the classes are disjoint.

---

### Q21 — Organism disjointWith disorder (pathogen is NOT a disorder)

- **Prompt:** "Is there any overlap between the classification of pathogens and disorders?"
- **OWL axiom:** `organism owl:disjointWith disorder`
- **Entity:** `SCENARIO.measles_pathogen` (typed as `pathogen`, subclass of `organism`)
- **Check method:** SPARQL ASK `{ ?entity a disorder }` — returns False (not a member)

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "No, a pathogen cannot be a disorder." | 1.0 | **1.0** | Extracts "pathogen", "disorder". Negation "cannot" detected. Graph confirms pathogen is NOT a disorder. Negation matches graph negative → consistent. |
| 2 | "A pathogen is a disorder." | 1.0 | **0.0** | Same extraction. No negation. Affirming a false claim → inconsistent. |
| 3 | "No, a microbe cannot be an ailment." | 0.65 | **1.0** | "microbe"→"pathogen" (0.76), "ailment"→"disorder" (0.65). Negation detected. Matches graph. |
| 4 | "A microbe is an ailment." | 0.65 | **0.0** | Same similarity matches. No negation. Affirming false claim. |
| 5 | "They are fundamentally different categories." | 1.0 | **non-parse** | No ontology terms. |

---

### Q22 — Pathogenic disposition disjointWith disease

- **Prompt:** "What is the relationship between a pathogenic disposition and a disease?"
- **OWL axiom:** `pathogenic_disposition owl:disjointWith disease`
- **Entity:** `SCENARIO.pathogenic_disposition`
- **Check method:** SPARQL ASK `{ ?entity a disease }` — returns False

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "No, a pathogenic disposition is not a disease." | 1.0 | **1.0** | Extracts "pathogenic disposition", "disease". Negation "not" detected. Entity is not a disease (disjoint). Matches graph. |
| 2 | "A pathogenic disposition is a disease." | 1.0 | **0.0** | No negation. Affirming a false claim. |
| 3 | "No, virulence is not an illness." | 0.65 | **1.0** | "virulence"→"pathogenic disposition" (0.80), "illness"→"disease" (1.00). Negation detected. Matches graph. |
| 4 | "Virulence is an illness." | 0.65 | **0.0** | Same similarity matches. No negation. Affirming false claim. |
| 5 | "They refer to different concepts entirely." | 1.0 | **non-parse** | No ontology terms. |

---

### Q23 — Pathogenic disposition disjointWith immunocompetence

- **Prompt:** "Is there any ontological overlap between pathogenic disposition and immunocompetence?"
- **OWL axiom:** `pathogenic_disposition owl:disjointWith immunocompetence`
- **Entity:** `SCENARIO.pathogenic_disposition`
- **Check method:** SPARQL ASK `{ ?entity a immunocompetence }` — returns False

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "No, pathogenic disposition and immunocompetence are not the same." | 1.0 | **1.0** | Extracts "pathogenic disposition", "immunocompetence". Negation "not" detected. Matches graph. |
| 2 | "Pathogenic disposition is immunocompetence." | 1.0 | **0.0** | No negation. Affirming false claim. |
| 3 | "No, virulence is not the same as immunocompetence." | 0.65 | **1.0** | "virulence"→"pathogenic disposition" (0.80). "immunocompetence" exact match. Negation detected. |
| 4 | "Virulence is the same as immunocompetence." | 0.65 | **0.0** | Same matches. No negation. |
| 5 | "These are separate biological attributes." | 1.0 | **non-parse** | No ontology terms. |

---

### Q24 — Host is NOT a disease

- **Prompt:** "What is the ontological relationship between a host and disease?"
- **OWL axiom:** `immunocompetence owl:disjointWith disease` (host is an organism, not a disease)
- **Entity:** `SCENARIO.human_host` (typed as `host`, subclass of `organism`)
- **Check method:** SPARQL ASK `{ ?entity a disease }` — returns False

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "No, a host is not a disease." | 1.0 | **1.0** | Extracts "host", "disease". Negation "not" detected. Host is not a disease. Matches graph. |
| 2 | "A host is a disease." | 1.0 | **0.0** | No negation. Affirming false claim. |
| 3 | "No, a host is not an illness." | 0.65 | **1.0** | "illness"→"disease" (1.00). Negation detected. Matches graph. |
| 4 | "A host is an illness." | 0.65 | **0.0** | Same similarity match. No negation. |
| 5 | "The individual harbors the condition." | 1.0 | **non-parse** | No ontology terms ("individual", "condition" not in vocabulary). |

---

### Q25 — Material entity disjointWith immaterial entity (pathogen is material)

- **Prompt:** "What kind of entity is a pathogen — material, immaterial, or both?"
- **OWL axiom:** `material_entity owl:disjointWith immaterial_entity`
- **Entity:** `SCENARIO.measles_pathogen` (typed as `pathogen subClassOf organism subClassOf material_entity`)
- **Check method:** SPARQL ASK `{ ?entity a immaterial_entity }` — returns False

| # | Response | Threshold | Result | Explanation |
| --- | --- | --- | --- | --- |
| 1 | "No, a pathogen cannot be an immaterial entity." | 1.0 | **1.0** | Extracts "pathogen", "immaterial entity". Negation "cannot" detected. Pathogen is not immaterial. Matches graph. |
| 2 | "A pathogen is an immaterial entity." | 1.0 | **0.0** | No negation. Affirming false claim. |
| 3 | "No, a microbe cannot be an immaterial entity." | 0.65 | **1.0** | "microbe"→"pathogen" (0.76). Negation detected. Matches graph. |
| 4 | "A microbe is an immaterial entity." | 0.65 | **0.0** | Same similarity match. No negation. |
| 5 | "It has physical substance." | 1.0 | **non-parse** | No ontology terms. |
