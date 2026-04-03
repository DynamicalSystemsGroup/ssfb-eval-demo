# Question Bank Review — 25 Questions with Mocked Responses

This document lists every question in the evaluation bank, its ontological grounding, the three mocked test responses, and an explanation of why each receives its score.

## Scoring Logic

The scoring pipeline has three possible outcomes per response:

| Outcome | `parse_success` | `score` | Meaning |
| --- | --- | --- | --- |
| **Pass (1.0)** | `True` | `1.0` | Response contains ontology terms AND agrees with the ontological fact |
| **Fail (0.0)** | `True` | `0.0` | Response contains ontology terms BUT contradicts the ontological fact |
| **Non-parse** | `False` | N/A | Response contains no ontology terms — cannot be scored |

**Negation detection** determines response polarity. The spaCy dependency parser identifies `neg` dependencies, and a lexical fallback catches tokens like "not", "no", "cannot", "doesn't", etc. The response's polarity (affirming vs. negating) is combined with the graph truth to produce the final score.

---

## Q1–Q12: Class Membership (SPARQL ASK)

These questions test `entity rdf:type class` — either directly asserted or entailed via `rdfs:subClassOf` transitivity after OWL RL reasoning.

---

### Q1 — Epidemic instance is an epidemic

- **Prompt:** "In the context of infectious disease modeling, what type of event is a measles epidemic?"
- **OWL axiom:** `SCENARIO.measles_epidemic rdf:type APOLLO_SV:epidemic` (direct assertion)
- **Check method:** SPARQL ASK `{ ?entity a ?class }`

| Response | Result | Explanation |
| --- | --- | --- |
| "A measles epidemic is an epidemic event." | **1.0** | PhraseMatcher extracts "epidemic". No negation detected. Graph confirms `measles_epidemic a epidemic`. Affirming a true fact → consistent. |
| "A measles epidemic is not an epidemic." | **0.0** | PhraseMatcher extracts "epidemic". Negation "not" detected. Graph confirms `measles_epidemic a epidemic`. Negating a true fact → inconsistent. |
| "It is a sudden outbreak of illness." | **non-parse** | No ontology terms found by PhraseMatcher ("outbreak", "illness" are not in the APOLLO-SV vocabulary). Cannot evaluate. |

---

### Q2 — Epidemic is an infection in ecosystem (entailed)

- **Prompt:** "A measles epidemic involves infection spreading through a community. Is an epidemic a type of infection in ecosystem?"
- **OWL axiom:** `epidemic rdfs:subClassOf infection_in_ecosystem` → entails `measles_epidemic a infection_in_ecosystem`
- **Check method:** SPARQL ASK `{ ?entity a ?class }`

| Response | Result | Explanation |
| --- | --- | --- |
| "Yes, an epidemic is a type of infection in ecosystem." | **1.0** | Extracts "epidemic", "infection in ecosystem". No negation. Graph confirms membership (entailed via subClassOf). Affirming a true entailed fact → consistent. |
| "No, an epidemic is not an infection in ecosystem." | **0.0** | Extracts same terms. Negation "not" detected. Graph says it IS. Negating a true fact → inconsistent. |
| "It spreads through communities." | **non-parse** | No ontology terms. "communities" is not in the vocabulary. |

---

### Q3 — Vaccination strategy is a vaccination control strategy (direct)

- **Prompt:** "What type of control strategy is a vaccination control strategy?"
- **OWL axiom:** `SCENARIO.vaccination_strategy rdf:type vaccination_control_strategy` (direct)
- **Check method:** SPARQL ASK

| Response | Result | Explanation |
| --- | --- | --- |
| "It is a vaccination control strategy." | **1.0** | Extracts "vaccination control strategy". No negation. Graph confirms. |
| "It is not a vaccination control strategy." | **0.0** | Same extraction. Negation "not" detected. Negating a true fact. |
| "It is a plan for prevention." | **non-parse** | "plan" and "prevention" are not ontology labels. |

---

### Q4 — Vaccination control strategy is individual treatment control strategy (entailed)

- **Prompt:** "Is a vaccination control strategy a type of individual treatment control strategy?"
- **OWL axiom:** `vaccination_control_strategy rdfs:subClassOf individual_treatment_control_strategy`
- **Check method:** SPARQL ASK

| Response | Result | Explanation |
| --- | --- | --- |
| "Yes, a vaccination control strategy is an individual treatment control strategy." | **1.0** | Extracts both multi-word labels. No negation. Entailed membership confirmed by graph. |
| "No, a vaccination control strategy is not an individual treatment control strategy." | **0.0** | Same extraction. Negation "not" detected. Contradicts entailed fact. |
| "It targets specific patients." | **non-parse** | No ontology terms present. |

---

### Q5 — Vaccination control strategy is infectious disease control strategy (entailed chain)

- **Prompt:** "Would you classify a vaccination control strategy as an infectious disease control strategy?"
- **OWL axiom:** `vaccination_control_strategy subClassOf individual_treatment_control_strategy subClassOf infectious_disease_control_strategy` (two-hop entailment)
- **Check method:** SPARQL ASK

| Response | Result | Explanation |
| --- | --- | --- |
| "A vaccination control strategy is an infectious disease control strategy." | **1.0** | Both labels extracted. No negation. Two-hop subClassOf entailment materialized by OWL RL. |
| "A vaccination control strategy is not an infectious disease control strategy." | **0.0** | Negation detected. Contradicts the entailed two-hop relationship. |
| "It helps prevent spread." | **non-parse** | No ontology terms. |

---

### Q6 — Quarantine control strategy is infectious disease control strategy (entailed)

- **Prompt:** "Is a quarantine control strategy a type of infectious disease control strategy?"
- **OWL axiom:** `quarantine_control_strategy rdfs:subClassOf infectious_disease_control_strategy`
- **Check method:** SPARQL ASK

| Response | Result | Explanation |
| --- | --- | --- |
| "Yes, a quarantine control strategy is an infectious disease control strategy." | **1.0** | Both labels extracted. No negation. Entailed membership confirmed. |
| "No, a quarantine control strategy is not an infectious disease control strategy." | **0.0** | Negation "not" detected. Contradicts entailed subclass relationship. |
| "It involves isolating people." | **non-parse** | No ontology terms. |

---

### Q7 — Vaccination treatment is a vaccination (direct)

- **Prompt:** "What is the classification of vaccination as a medical intervention?"
- **OWL axiom:** `SCENARIO.vacc_treatment rdf:type vaccination` (direct)
- **Check method:** SPARQL ASK

| Response | Result | Explanation |
| --- | --- | --- |
| "Vaccination is classified as a vaccination procedure." | **1.0** | Extracts "vaccination". No negation. Direct type assertion confirmed. |
| "Vaccination is not actually a vaccination in the formal sense." | **0.0** | Extracts "vaccination". Negation "not" detected. Contradicts direct assertion. |
| "It is an injection given to patients." | **non-parse** | No ontology terms. |

---

### Q8 — Vaccination is a treatment (entailed)

- **Prompt:** "Is vaccination considered a type of treatment in infectious disease management?"
- **OWL axiom:** `vaccination rdfs:subClassOf treatment`
- **Check method:** SPARQL ASK

| Response | Result | Explanation |
| --- | --- | --- |
| "Yes, vaccination is a type of treatment." | **1.0** | Extracts "vaccination", "treatment". No negation. Entailed via subClassOf. |
| "Vaccination is not a treatment." | **0.0** | Negation "not" detected. Contradicts entailed relationship. |
| "It is a preventive measure." | **non-parse** | "preventive measure" is not an ontology label. |

---

### Q9 — Drug treatment is a treatment (entailed)

- **Prompt:** "Is drug treatment classified as a type of treatment?"
- **OWL axiom:** `drug_treatment rdfs:subClassOf treatment`
- **Check method:** SPARQL ASK

| Response | Result | Explanation |
| --- | --- | --- |
| "Drug treatment is a type of treatment." | **1.0** | Extracts "drug treatment", "treatment". No negation. Entailed. |
| "Drug treatment is not a treatment." | **0.0** | Negation detected. Contradicts entailed fact. |
| "Patients take medication." | **non-parse** | No ontology terms. |

---

### Q10 — Pathogen is a pathogen (direct)

- **Prompt:** "In the measles scenario, what role does the causative agent play? Is it classified as a pathogen?"
- **OWL axiom:** `SCENARIO.measles_pathogen rdf:type pathogen` (direct)
- **Check method:** SPARQL ASK

| Response | Result | Explanation |
| --- | --- | --- |
| "The causative agent is classified as a pathogen." | **1.0** | Extracts "pathogen". No negation. Direct assertion confirmed. |
| "The agent is not a pathogen." | **0.0** | Extracts "pathogen". Negation "not" detected. Contradicts. |
| "It causes illness in people." | **non-parse** | No ontology terms. |

---

### Q11 — Pathogen is an organism (entailed)

- **Prompt:** "Is a pathogen classified as a type of organism?"
- **OWL axiom:** `pathogen rdfs:subClassOf organism`
- **Check method:** SPARQL ASK

| Response | Result | Explanation |
| --- | --- | --- |
| "Yes, a pathogen is a type of organism." | **1.0** | Extracts "pathogen", "organism". No negation. Entailed via subClassOf. |
| "A pathogen is not an organism." | **0.0** | Negation detected. Contradicts entailed fact. |
| "It is a living thing." | **non-parse** | "living thing" is not an ontology label. |

---

### Q12 — Population infection survey is a population survey (entailed)

- **Prompt:** "Is a population infection survey a type of population survey?"
- **OWL axiom:** `population_infection_survey rdfs:subClassOf population_survey`
- **Check method:** SPARQL ASK

| Response | Result | Explanation |
| --- | --- | --- |
| "A population infection survey is a type of population survey." | **1.0** | Extracts both multi-word labels. No negation. Entailed. |
| "A population infection survey is not a population survey." | **0.0** | Negation detected. Contradicts entailed subclass relationship. |
| "It collects data on illness rates." | **non-parse** | No ontology terms. |

---

## Q13–Q20: Property Restriction (pyshacl)

These questions test `entity property value` — verified by constructing a SHACL NodeShape requiring the entity to have the expected property-value pair, then running pyshacl validation against the data graph.

---

### Q13 — Scenario is about ecosystem

- **Prompt:** "What is an infectious disease scenario about? Does it concern an ecosystem?"
- **OWL restriction:** `infectious_disease_scenario some is_about ecosystem`
- **Scenario assertion:** `SCENARIO.measles_scenario is_about SCENARIO.target_ecosystem`
- **Check method:** pyshacl — NodeShape requiring `measles_scenario → is_about → target_ecosystem`

| Response | Result | Explanation |
| --- | --- | --- |
| "An infectious disease scenario is about an ecosystem." | **1.0** | Extracts "infectious disease scenario", "ecosystem". No negation. pyshacl confirms the triple exists. Affirming a true property → consistent. |
| "An infectious disease scenario is not about an ecosystem." | **0.0** | Same extraction. Negation "not" detected. pyshacl confirms the triple exists, but response negates it → inconsistent. |
| "It models environmental conditions." | **non-parse** | No ontology terms. |

---

### Q14 — Infection acquisition causally upstream of infection

- **Prompt:** "Is infection acquisition causally upstream of infection? Does acquiring an infection lead to the infection process?"
- **OWL restriction:** `infection_acquisition some causally_upstream_of infection`
- **Scenario assertion:** `SCENARIO.measles_acquisition causally_upstream_of SCENARIO.measles_infection`
- **Check method:** pyshacl

| Response | Result | Explanation |
| --- | --- | --- |
| "Infection acquisition leads to infection." | **1.0** | Extracts "infection acquisition", "infection". No negation. pyshacl confirms. |
| "Infection acquisition does not lead to infection." | **0.0** | Negation "not" detected. Triple exists but response denies it. |
| "Exposure causes illness." | **non-parse** | "exposure" and "illness" are not ontology labels. |

---

### Q15 — Infection immediately preceded by infection acquisition

- **Prompt:** "Is infection immediately preceded by infection acquisition?"
- **OWL restriction:** `infection some immediately_preceded_by infection_acquisition`
- **Scenario assertion:** `SCENARIO.measles_infection immediately_preceded_by SCENARIO.measles_acquisition`
- **Check method:** pyshacl

| Response | Result | Explanation |
| --- | --- | --- |
| "Infection is preceded by infection acquisition." | **1.0** | Extracts "infection", "infection acquisition". No negation. pyshacl confirms. |
| "Infection is not preceded by infection acquisition." | **0.0** | Negation detected. Contradicts the asserted relationship. |
| "One stage follows another in sequence." | **non-parse** | No ontology terms. |

---

### Q16 — Pathogen bearer of pathogenic disposition

- **Prompt:** "Does a pathogen bear a pathogenic disposition? Is pathogenicity a characteristic of the pathogen?"
- **OWL restriction:** `pathogen some bearer_of infectiousness`
- **Scenario assertion:** `SCENARIO.measles_pathogen bearer_of SCENARIO.pathogenic_disposition`
- **Check method:** pyshacl

| Response | Result | Explanation |
| --- | --- | --- |
| "A pathogen bears a pathogenic disposition." | **1.0** | Extracts "pathogen", "pathogenic disposition". No negation. pyshacl confirms. |
| "A pathogen does not bear a pathogenic disposition." | **0.0** | Negation "not" detected. Triple exists but response denies it. |
| "It has the ability to cause harm." | **non-parse** | No ontology terms ("harm", "ability" not in vocabulary). |

---

### Q17 — Vaccination has participant host

- **Prompt:** "Does vaccination have a host as a participant?"
- **OWL restriction:** `vaccination some has_participant` (host)
- **Scenario assertion:** `SCENARIO.vacc_treatment has_participant SCENARIO.human_host`
- **Check method:** pyshacl

| Response | Result | Explanation |
| --- | --- | --- |
| "Vaccination has a host as participant." | **1.0** | Extracts "vaccination", "host". No negation. pyshacl confirms. |
| "Vaccination does not have a host as participant." | **0.0** | Negation "not" detected. Triple exists but response denies it. |
| "A patient receives the injection." | **non-parse** | No ontology terms. |

---

### Q18 — Epidemic occurs in ecosystem

- **Prompt:** "Does an epidemic occur in an ecosystem?"
- **Scenario assertion:** `SCENARIO.measles_epidemic occurs_in SCENARIO.target_ecosystem`
- **Check method:** pyshacl

| Response | Result | Explanation |
| --- | --- | --- |
| "An epidemic occurs in an ecosystem." | **1.0** | Extracts "epidemic", "ecosystem". No negation. pyshacl confirms. |
| "An epidemic does not occur in an ecosystem." | **0.0** | Negation detected. Contradicts asserted triple. |
| "It happens in a community." | **non-parse** | "community" not in vocabulary. |

---

### Q19 — Infection acquisition has participant pathogen

- **Prompt:** "Does infection acquisition involve a pathogen as a participant?"
- **Scenario assertion:** `SCENARIO.measles_acquisition has_participant SCENARIO.measles_pathogen`
- **Check method:** pyshacl

| Response | Result | Explanation |
| --- | --- | --- |
| "Infection acquisition involves a pathogen." | **1.0** | Extracts "infection acquisition", "pathogen". No negation. pyshacl confirms. |
| "Infection acquisition does not involve a pathogen." | **0.0** | Negation detected. Triple exists but response denies it. |
| "The microbe enters the body." | **non-parse** | No ontology terms. |

---

### Q20 — Vaccination does NOT have pathogen as participant (negative test)

- **Prompt:** "Does vaccination directly involve a pathogen as a participant?"
- **Graph fact:** The triple `SCENARIO.vacc_treatment has_participant SCENARIO.measles_pathogen` is **absent** from the graph. pyshacl validation **fails** (non-conforming).
- **Check method:** pyshacl — this is a negative test: the SHACL shape expects a triple that doesn't exist.

| Response | Result | Explanation |
| --- | --- | --- |
| "Vaccination does not involve a pathogen as participant." | **1.0** | Extracts "vaccination", "pathogen". Negation "not" detected. pyshacl says the triple is absent (conforms=False). Response negates an absent property → **consistent** (correctly denying something that isn't there). |
| "Vaccination involves a pathogen as participant." | **0.0** | Same extraction. No negation. pyshacl says the triple is absent. Response affirms an absent property → **inconsistent** (claiming something the graph doesn't support). |
| "The procedure targets the immune system." | **non-parse** | No ontology terms. |

---

## Q21–Q25: Disjointness (SPARQL ASK)

These questions test `owl:disjointWith` constraints. The check verifies that the entity is NOT a member of the disjoint class. Disjointness questions expect **negation** for a consistent response — "No, X cannot be Y" is the correct answer when the classes are disjoint.

---

### Q21 — Organism disjointWith disorder (pathogen is NOT a disorder)

- **Prompt:** "Can a pathogen, which is an organism, also be classified as a disorder?"
- **OWL axiom:** `organism owl:disjointWith disorder`
- **Entity:** `SCENARIO.measles_pathogen` (typed as `pathogen`, which is a subclass of `organism`)
- **Check method:** SPARQL ASK `{ ?entity a disorder }` — returns False (not a member)

| Response | Result | Explanation |
| --- | --- | --- |
| "No, a pathogen cannot be a disorder." | **1.0** | Extracts "pathogen", "disorder". Negation "cannot" detected. Graph confirms pathogen is NOT a disorder. Negation matches the graph's negative → consistent. |
| "A pathogen is a disorder." | **0.0** | Same extraction. No negation. Graph says it's NOT a disorder. Affirming a false claim → inconsistent. |
| "They are fundamentally different categories." | **non-parse** | No ontology terms. |

---

### Q22 — Pathogenic disposition disjointWith disease

- **Prompt:** "Is a pathogenic disposition the same as a disease? Can something be both?"
- **OWL axiom:** `pathogenic_disposition owl:disjointWith disease`
- **Entity:** `SCENARIO.pathogenic_disposition` (typed as `pathogenic_disposition`)
- **Check method:** SPARQL ASK `{ ?entity a disease }` — returns False

| Response | Result | Explanation |
| --- | --- | --- |
| "No, a pathogenic disposition is not a disease." | **1.0** | Extracts "pathogenic disposition", "disease". Negation "not" detected. Entity is not a disease (disjoint). Negation matches graph → consistent. |
| "A pathogenic disposition is a disease." | **0.0** | No negation. Graph says it's not a disease. Affirming a false claim → inconsistent. |
| "They refer to different concepts." | **non-parse** | No ontology terms. |

---

### Q23 — Pathogenic disposition disjointWith immunocompetence

- **Prompt:** "Can a pathogenic disposition also be classified as immunocompetence?"
- **OWL axiom:** `pathogenic_disposition owl:disjointWith immunocompetence`
- **Entity:** `SCENARIO.pathogenic_disposition`
- **Check method:** SPARQL ASK `{ ?entity a immunocompetence }` — returns False

| Response | Result | Explanation |
| --- | --- | --- |
| "No, pathogenic disposition and immunocompetence are not the same." | **1.0** | Extracts "pathogenic disposition", "immunocompetence". Negation "not" detected. Entity is not immunocompetence. Negation matches → consistent. |
| "Pathogenic disposition is immunocompetence." | **0.0** | No negation. Entity is NOT immunocompetence. Affirming a false claim → inconsistent. |
| "These are separate biological attributes." | **non-parse** | No ontology terms. |

---

### Q24 — Host is NOT a disease

- **Prompt:** "Can immunocompetence be classified as a disease?"
- **OWL axiom:** `immunocompetence owl:disjointWith disease`
- **Entity:** `SCENARIO.human_host` (typed as `host`, subclass of `organism` — not `disease`)
- **Check method:** SPARQL ASK `{ ?entity a disease }` — returns False

| Response | Result | Explanation |
| --- | --- | --- |
| "No, a host is not a disease." | **1.0** | Extracts "host", "disease". Negation "not" detected. Host is not a disease. Negation matches → consistent. |
| "A host is a disease." | **0.0** | No negation. Host is NOT a disease. Affirming a false claim → inconsistent. |
| "The individual harbors the condition." | **non-parse** | No ontology terms ("individual", "condition" not in vocabulary). |

---

### Q25 — Material entity disjointWith immaterial entity (pathogen is material)

- **Prompt:** "A pathogen is a material entity. Can it also be classified as an immaterial entity?"
- **OWL axiom:** `material_entity owl:disjointWith immaterial_entity`
- **Entity:** `SCENARIO.measles_pathogen` (typed as `pathogen subClassOf organism subClassOf material_entity`)
- **Check method:** SPARQL ASK `{ ?entity a immaterial_entity }` — returns False

| Response | Result | Explanation |
| --- | --- | --- |
| "No, a pathogen cannot be an immaterial entity." | **1.0** | Extracts "pathogen", "immaterial entity". Negation "cannot" detected. Pathogen is not immaterial. Negation matches → consistent. |
| "A pathogen is an immaterial entity." | **0.0** | No negation. Pathogen is NOT immaterial. Affirming false claim → inconsistent. |
| "It has physical substance." | **non-parse** | No ontology terms. |
