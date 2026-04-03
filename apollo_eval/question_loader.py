"""Builds 25 concrete questions for a measles epidemic scenario.

The question bank targets one infectious disease scenario in the APOLLO-SV
ontology. Scenario instances are added to the already-expanded graph, and
questions test class membership (SPARQL ASK), property restrictions (pyshacl),
and disjointness constraints (SPARQL ASK).

All entity/class labels used in questions must already exist in the ontology
vocabulary (PhraseMatcher) — the scenario instances are typed using existing
APOLLO-SV classes whose labels were extracted during vocabulary building.
"""

import rdflib
from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL

import owlrl

from apollo_eval.ontology import Ontology
from apollo_eval.question import (
    Question,
    ClassMembershipQuestion,
    PropertyRestrictionQuestion,
    DisjointnessQuestion,
)

# APOLLO-SV and related ontology IRIs
OBO = Namespace("http://purl.obolibrary.org/obo/")

# Scenario instance namespace 
# example.org used to avoid dereferenceable IRIs that might conflict with real data
SCENARIO = Namespace("http://example.org/scenario/measles_epidemic/")

# --- APOLLO-SV class IRIs ---
# Diseases
INFECTIOUS_DISEASE = OBO["APOLLO_SV_00000239"]
DISEASE = OBO["OGMS_0000031"]
EPIDEMIC = OBO["APOLLO_SV_00000298"]
INFECTION_IN_ECOSYSTEM = OBO["APOLLO_SV_00000306"]

# Processes
INFECTION = OBO["APOLLO_SV_00000114"]
INFECTION_ACQUISITION = OBO["APOLLO_SV_00000115"]

# Control strategies
INFECTIOUS_DISEASE_CONTROL_STRATEGY = OBO["APOLLO_SV_00000086"]
INDIVIDUAL_TREATMENT_CONTROL_STRATEGY = OBO["APOLLO_SV_00000194"]
VACCINATION_CONTROL_STRATEGY = OBO["APOLLO_SV_00000136"]
QUARANTINE_CONTROL_STRATEGY = OBO["APOLLO_SV_00000327"]

# Treatments
TREATMENT = OBO["OGMS_0000090"]
VACCINATION = OBO["APOLLO_SV_00000142"]
DRUG_TREATMENT = OBO["APOLLO_SV_00000318"]

# Entities
PATHOGEN = OBO["APOLLO_SV_00000237"]
HOST = OBO["IDO_0000531"]
ORGANISM = OBO["OBI_0100026"]
ECOSYSTEM = OBO["APOLLO_SV_00000097"]

# Data / info
INFECTIOUS_DISEASE_SCENARIO = OBO["APOLLO_SV_00000184"]
CASE_DEFINITION = OBO["APOLLO_SV_00000296"]
POPULATION_INFECTION_SURVEY = OBO["APOLLO_SV_00000155"]
POPULATION_SURVEY = OBO["APOLLO_SV_00000152"]
BASIC_REPRODUCTION_NUMBER = OBO["APOLLO_SV_00000002"]
VACCINATION_EFFICACY = OBO["APOLLO_SV_00000025"]
EPIDEMIC_MODEL = OBO["APOLLO_SV_00000001"]

# Dispositions
PATHOGENIC_DISPOSITION = OBO["IDO_0000450"]
IMMUNOCOMPETENCE = OBO["IDO_0000618"]

# BFO / upper-level
MATERIAL_ENTITY = OBO["BFO_0000040"]
DISORDER = OBO["OGMS_0000045"]
PROCESS = OBO["BFO_0000015"]
PLAN_SPECIFICATION = OBO["IAO_0000104"]

# --- Property IRIs ---
IS_ABOUT = OBO["IAO_0000136"]
CAUSALLY_UPSTREAM_OF = OBO["RO_0002411"]
IMMEDIATELY_PRECEDED_BY = OBO["RO_0002087"]
BEARER_OF = OBO["RO_0000053"]
HAS_PARTICIPANT = OBO["RO_0000057"]
OCCURS_IN = OBO["BFO_0000066"]


def add_scenario_instances(graph: rdflib.Graph) -> None:
    """Add measles epidemic scenario instances to the ontology graph.

    These instances provide the grounding for the question bank. They are
    typed using existing APOLLO-SV classes so that OWL RL entailments
    (already materialized) apply to them via rdf:type propagation.
    """
    # Scenario container
    graph.add((SCENARIO.measles_scenario, RDF.type, INFECTIOUS_DISEASE_SCENARIO))
    graph.add((SCENARIO.measles_scenario, IS_ABOUT, SCENARIO.target_ecosystem))

    # Ecosystem
    graph.add((SCENARIO.target_ecosystem, RDF.type, ECOSYSTEM))

    # Epidemic
    graph.add((SCENARIO.measles_epidemic, RDF.type, EPIDEMIC))
    graph.add((SCENARIO.measles_epidemic, OCCURS_IN, SCENARIO.target_ecosystem))

    # Infection and acquisition
    graph.add((SCENARIO.measles_infection, RDF.type, INFECTION))
    graph.add((SCENARIO.measles_acquisition, RDF.type, INFECTION_ACQUISITION))
    graph.add((SCENARIO.measles_acquisition, CAUSALLY_UPSTREAM_OF, SCENARIO.measles_infection))
    graph.add((SCENARIO.measles_infection, IMMEDIATELY_PRECEDED_BY, SCENARIO.measles_acquisition))

    # Pathogen and host
    graph.add((SCENARIO.measles_pathogen, RDF.type, PATHOGEN))
    graph.add((SCENARIO.pathogenic_disposition, RDF.type, PATHOGENIC_DISPOSITION))
    graph.add((SCENARIO.measles_pathogen, BEARER_OF, SCENARIO.pathogenic_disposition))
    graph.add((SCENARIO.human_host, RDF.type, HOST))
    graph.add((SCENARIO.measles_acquisition, HAS_PARTICIPANT, SCENARIO.measles_pathogen))

    # Control strategies
    graph.add((SCENARIO.vaccination_strategy, RDF.type, VACCINATION_CONTROL_STRATEGY))
    graph.add((SCENARIO.quarantine_strategy, RDF.type, QUARANTINE_CONTROL_STRATEGY))

    # Treatments
    graph.add((SCENARIO.vacc_treatment, RDF.type, VACCINATION))
    graph.add((SCENARIO.vacc_treatment, HAS_PARTICIPANT, SCENARIO.human_host))
    graph.add((SCENARIO.drug_treatment, RDF.type, DRUG_TREATMENT))

    # Data and parameters
    graph.add((SCENARIO.case_def, RDF.type, CASE_DEFINITION))
    graph.add((SCENARIO.pop_survey, RDF.type, POPULATION_INFECTION_SURVEY))
    graph.add((SCENARIO.basic_r0, RDF.type, BASIC_REPRODUCTION_NUMBER))
    graph.add((SCENARIO.vacc_efficacy, RDF.type, VACCINATION_EFFICACY))
    graph.add((SCENARIO.epi_model, RDF.type, EPIDEMIC_MODEL))


def build_question_bank(ontology: Ontology) -> list[Question]:
    """Build the fixed question bank of 25 questions for the measles scenario.

    Must be called after the ontology is loaded, reasoned, and vocabulary built.
    Adds scenario instances to the graph, re-applies reasoning to materialize
    entailed types for the new instances, then creates questions against them.
    """
    add_scenario_instances(ontology.graph)
    # Re-reason so entailed types propagate to scenario instances
    # (e.g., vaccination_strategy a vaccination_control_strategy →
    #  vaccination_strategy a individual_treatment_control_strategy via subClassOf)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(ontology.graph)

    questions = []

    # =====================================================================
    # CLASS MEMBERSHIP QUESTIONS (12) — SPARQL ASK
    # =====================================================================

    # Q1: Direct type — epidemic instance is an epidemic
    # OWL axiom: SCENARIO.measles_epidemic rdf:type APOLLO_SV:epidemic
    questions.append(ClassMembershipQuestion(
        question_id="c3a1e8f0-0001-4000-8000-000000000001",
        prompt="In the context of infectious disease modeling, what type of event is a measles epidemic?",
        entity_iri=SCENARIO.measles_epidemic,
        class_iri=EPIDEMIC,
        entity_label="epidemic",
        class_label="epidemic",
    ))

    # Q2: Entailed — epidemic is an infection in ecosystem (epidemic subClassOf infection_in_ecosystem)
    # OWL axiom: epidemic rdfs:subClassOf infection_in_ecosystem
    questions.append(ClassMembershipQuestion(
        question_id="c3a1e8f0-0001-4000-8000-000000000002",
        prompt="A measles epidemic involves infection spreading through a community. Is an epidemic a type of infection in ecosystem?",
        entity_iri=SCENARIO.measles_epidemic,
        class_iri=INFECTION_IN_ECOSYSTEM,
        entity_label="epidemic",
        class_label="infection in ecosystem",
    ))

    # Q3: Direct type — vaccination strategy is a vaccination control strategy
    # OWL axiom: SCENARIO.vaccination_strategy rdf:type vaccination_control_strategy
    questions.append(ClassMembershipQuestion(
        question_id="c3a1e8f0-0001-4000-8000-000000000003",
        prompt="What type of control strategy is a vaccination control strategy?",
        entity_iri=SCENARIO.vaccination_strategy,
        class_iri=VACCINATION_CONTROL_STRATEGY,
        entity_label="vaccination control strategy",
        class_label="vaccination control strategy",
    ))

    # Q4: Entailed — vaccination strategy is an individual treatment control strategy
    # OWL axiom: vaccination_control_strategy subClassOf individual_treatment_control_strategy
    questions.append(ClassMembershipQuestion(
        question_id="c3a1e8f0-0001-4000-8000-000000000004",
        prompt="Is a vaccination control strategy a type of individual treatment control strategy?",
        entity_iri=SCENARIO.vaccination_strategy,
        class_iri=INDIVIDUAL_TREATMENT_CONTROL_STRATEGY,
        entity_label="vaccination control strategy",
        class_label="individual treatment control strategy",
    ))

    # Q5: Entailed — vaccination strategy is an infectious disease control strategy
    # OWL axiom: vaccination_control_strategy subClassOf ... subClassOf infectious_disease_control_strategy
    questions.append(ClassMembershipQuestion(
        question_id="c3a1e8f0-0001-4000-8000-000000000005",
        prompt="Would you classify a vaccination control strategy as an infectious disease control strategy?",
        entity_iri=SCENARIO.vaccination_strategy,
        class_iri=INFECTIOUS_DISEASE_CONTROL_STRATEGY,
        entity_label="vaccination control strategy",
        class_label="infectious disease control strategy",
    ))

    # Q6: Entailed — quarantine strategy is an infectious disease control strategy
    # OWL axiom: quarantine_control_strategy subClassOf infectious_disease_control_strategy
    questions.append(ClassMembershipQuestion(
        question_id="c3a1e8f0-0001-4000-8000-000000000006",
        prompt="Is a quarantine control strategy a type of infectious disease control strategy?",
        entity_iri=SCENARIO.quarantine_strategy,
        class_iri=INFECTIOUS_DISEASE_CONTROL_STRATEGY,
        entity_label="quarantine control strategy",
        class_label="infectious disease control strategy",
    ))

    # Q7: Direct type — vaccination treatment is a vaccination
    # OWL axiom: SCENARIO.vacc_treatment rdf:type vaccination
    questions.append(ClassMembershipQuestion(
        question_id="c3a1e8f0-0001-4000-8000-000000000007",
        prompt="What is the classification of vaccination as a medical intervention?",
        entity_iri=SCENARIO.vacc_treatment,
        class_iri=VACCINATION,
        entity_label="vaccination",
        class_label="vaccination",
    ))

    # Q8: Entailed — vaccination is a treatment
    # OWL axiom: vaccination subClassOf treatment
    questions.append(ClassMembershipQuestion(
        question_id="c3a1e8f0-0001-4000-8000-000000000008",
        prompt="Is vaccination considered a type of treatment in infectious disease management?",
        entity_iri=SCENARIO.vacc_treatment,
        class_iri=TREATMENT,
        entity_label="vaccination",
        class_label="treatment",
    ))

    # Q9: Entailed — drug treatment is a treatment
    # OWL axiom: drug_treatment subClassOf treatment
    questions.append(ClassMembershipQuestion(
        question_id="c3a1e8f0-0001-4000-8000-000000000009",
        prompt="Is drug treatment classified as a type of treatment?",
        entity_iri=SCENARIO.drug_treatment,
        class_iri=TREATMENT,
        entity_label="drug treatment",
        class_label="treatment",
    ))

    # Q10: Direct type — pathogen is a pathogen
    # OWL axiom: SCENARIO.measles_pathogen rdf:type pathogen
    questions.append(ClassMembershipQuestion(
        question_id="c3a1e8f0-0001-4000-8000-000000000010",
        prompt="In the measles scenario, what role does the causative agent play? Is it classified as a pathogen?",
        entity_iri=SCENARIO.measles_pathogen,
        class_iri=PATHOGEN,
        entity_label="pathogen",
        class_label="pathogen",
    ))

    # Q11: Entailed — pathogen is an organism
    # OWL axiom: pathogen subClassOf organism
    questions.append(ClassMembershipQuestion(
        question_id="c3a1e8f0-0001-4000-8000-000000000011",
        prompt="Is a pathogen classified as a type of organism?",
        entity_iri=SCENARIO.measles_pathogen,
        class_iri=ORGANISM,
        entity_label="pathogen",
        class_label="organism",
    ))

    # Q12: Entailed — population infection survey is a population survey
    # OWL axiom: population_infection_survey subClassOf population_survey
    questions.append(ClassMembershipQuestion(
        question_id="c3a1e8f0-0001-4000-8000-000000000012",
        prompt="Is a population infection survey a type of population survey?",
        entity_iri=SCENARIO.pop_survey,
        class_iri=POPULATION_SURVEY,
        entity_label="population infection survey",
        class_label="population survey",
    ))

    # =====================================================================
    # PROPERTY RESTRICTION QUESTIONS (8) — pyshacl
    # =====================================================================

    # Q13: measles scenario is about ecosystem
    # OWL restriction: infectious_disease_scenario some is_about ecosystem
    questions.append(PropertyRestrictionQuestion(
        question_id="c3a1e8f0-0002-4000-8000-000000000013",
        prompt="What is an infectious disease scenario about? Does it concern an ecosystem?",
        entity_iri=SCENARIO.measles_scenario,
        property_iri=IS_ABOUT,
        value_iri=SCENARIO.target_ecosystem,
        entity_label="infectious disease scenario",
        value_label="ecosystem",
    ))

    # Q14: infection acquisition causally upstream of infection
    # OWL restriction: infection_acquisition some causally_upstream_of infection
    questions.append(PropertyRestrictionQuestion(
        question_id="c3a1e8f0-0002-4000-8000-000000000014",
        prompt="Is infection acquisition causally upstream of infection? Does acquiring an infection lead to the infection process?",
        entity_iri=SCENARIO.measles_acquisition,
        property_iri=CAUSALLY_UPSTREAM_OF,
        value_iri=SCENARIO.measles_infection,
        entity_label="infection acquisition",
        value_label="infection",
    ))

    # Q15: infection immediately preceded by infection acquisition
    # OWL restriction: infection some immediately_preceded_by infection_acquisition
    questions.append(PropertyRestrictionQuestion(
        question_id="c3a1e8f0-0002-4000-8000-000000000015",
        prompt="Is infection immediately preceded by infection acquisition?",
        entity_iri=SCENARIO.measles_infection,
        property_iri=IMMEDIATELY_PRECEDED_BY,
        value_iri=SCENARIO.measles_acquisition,
        entity_label="infection",
        value_label="infection acquisition",
    ))

    # Q16: pathogen bearer of pathogenic disposition
    # OWL restriction: pathogen some bearer_of infectiousness (via pathogenic_disposition)
    questions.append(PropertyRestrictionQuestion(
        question_id="c3a1e8f0-0002-4000-8000-000000000016",
        prompt="Does a pathogen bear a pathogenic disposition? Is pathogenicity a characteristic of the pathogen?",
        entity_iri=SCENARIO.measles_pathogen,
        property_iri=BEARER_OF,
        value_iri=SCENARIO.pathogenic_disposition,
        entity_label="pathogen",
        value_label="pathogenic disposition",
    ))

    # Q17: vaccination has participant host
    # OWL restriction: vaccination some has_participant (host)
    questions.append(PropertyRestrictionQuestion(
        question_id="c3a1e8f0-0002-4000-8000-000000000017",
        prompt="Does vaccination have a host as a participant?",
        entity_iri=SCENARIO.vacc_treatment,
        property_iri=HAS_PARTICIPANT,
        value_iri=SCENARIO.human_host,
        entity_label="vaccination",
        value_label="host",
    ))

    # Q18: epidemic occurs in ecosystem
    # Scenario assertion: measles_epidemic occurs_in target_ecosystem
    questions.append(PropertyRestrictionQuestion(
        question_id="c3a1e8f0-0002-4000-8000-000000000018",
        prompt="Does an epidemic occur in an ecosystem?",
        entity_iri=SCENARIO.measles_epidemic,
        property_iri=OCCURS_IN,
        value_iri=SCENARIO.target_ecosystem,
        entity_label="epidemic",
        value_label="ecosystem",
    ))

    # Q19: infection acquisition has participant pathogen
    # Scenario assertion: measles_acquisition has_participant measles_pathogen
    questions.append(PropertyRestrictionQuestion(
        question_id="c3a1e8f0-0002-4000-8000-000000000019",
        prompt="Does infection acquisition involve a pathogen as a participant?",
        entity_iri=SCENARIO.measles_acquisition,
        property_iri=HAS_PARTICIPANT,
        value_iri=SCENARIO.measles_pathogen,
        entity_label="infection acquisition",
        value_label="pathogen",
    ))

    # Q20: Negative — vaccination does NOT have pathogen as participant (not asserted)
    # Tests that absence of a triple is detected as inconsistent
    questions.append(PropertyRestrictionQuestion(
        question_id="c3a1e8f0-0002-4000-8000-000000000020",
        prompt="Does vaccination directly involve a pathogen as a participant?",
        entity_iri=SCENARIO.vacc_treatment,
        property_iri=HAS_PARTICIPANT,
        value_iri=SCENARIO.measles_pathogen,
        entity_label="vaccination",
        value_label="pathogen",
    ))

    # =====================================================================
    # DISJOINTNESS QUESTIONS (5) — SPARQL ASK
    # =====================================================================

    # Q21: organism disjointWith disorder
    # OWL axiom: organism owl:disjointWith disorder
    questions.append(DisjointnessQuestion(
        question_id="c3a1e8f0-0003-4000-8000-000000000021",
        prompt="Can a pathogen, which is an organism, also be classified as a disorder?",
        entity_iri=SCENARIO.measles_pathogen,
        disjoint_class_iri=DISORDER,
        entity_label="pathogen",
        disjoint_class_label="disorder",
    ))

    # Q22: pathogenic disposition disjointWith disease
    # OWL axiom: pathogenic_disposition owl:disjointWith disease
    questions.append(DisjointnessQuestion(
        question_id="c3a1e8f0-0003-4000-8000-000000000022",
        prompt="Is a pathogenic disposition the same as a disease? Can something be both?",
        entity_iri=SCENARIO.pathogenic_disposition,
        disjoint_class_iri=DISEASE,
        entity_label="pathogenic disposition",
        disjoint_class_label="disease",
    ))

    # Q23: pathogenic disposition disjointWith immunocompetence
    # OWL axiom: pathogenic_disposition owl:disjointWith immunocompetence
    questions.append(DisjointnessQuestion(
        question_id="c3a1e8f0-0003-4000-8000-000000000023",
        prompt="Can a pathogenic disposition also be classified as immunocompetence?",
        entity_iri=SCENARIO.pathogenic_disposition,
        disjoint_class_iri=IMMUNOCOMPETENCE,
        entity_label="pathogenic disposition",
        disjoint_class_label="immunocompetence",
    ))

    # Q24: immunocompetence disjointWith disease
    # OWL axiom: immunocompetence owl:disjointWith disease
    questions.append(DisjointnessQuestion(
        question_id="c3a1e8f0-0003-4000-8000-000000000024",
        prompt="Can immunocompetence be classified as a disease?",
        entity_iri=SCENARIO.human_host,  # host, not typed as disease
        disjoint_class_iri=DISEASE,
        entity_label="host",
        disjoint_class_label="disease",
    ))

    # Q25: material entity disjointWith immaterial entity — pathogen is material, not immaterial
    # OWL axiom: material_entity owl:disjointWith immaterial_entity
    questions.append(DisjointnessQuestion(
        question_id="c3a1e8f0-0003-4000-8000-000000000025",
        prompt="A pathogen is a material entity. Can it also be classified as an immaterial entity?",
        entity_iri=SCENARIO.measles_pathogen,
        disjoint_class_iri=OBO["BFO_0000141"],  # immaterial entity
        entity_label="pathogen",
        disjoint_class_label="immaterial entity",
    ))

    assert len(questions) == 25, f"Expected 25 questions, got {len(questions)}"
    return questions


def get_question_map(questions: list[Question]) -> dict[str, Question]:
    """Return a mapping from question_id to Question for evaluation lookups."""
    return {q.question_id: q for q in questions}
